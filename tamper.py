import fitz  # PyMuPDF
import hashlib
import re
from datetime import datetime
from collections import Counter
import zlib
import struct

class PDFForensicAnalyzer:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.results = {}
        
    def analyze_file_structure(self):
        """Comprehensive PDF forensic analysis"""
        print(f"Analyzing PDF: {self.pdf_path}")
        print("=" * 60)
        
        # Basic file analysis
        self._analyze_basic_structure()
        
        # Metadata analysis
        self._analyze_metadata(threshold_days=30)
        
        # Object structure analysis
        self._analyze_objects()
        
        # Content stream analysis
        self._analyze_content_streams()
        
        # Font analysis
        self._analyze_fonts(unique_fonts_threshold=5)
        
        # Image analysis
        self._analyze_images()
        
        # Compression analysis
        self._analyze_compression()
        
        # Generate forensic report
        self._generate_report()

    def _analyze_basic_structure(self):
        """Analyze basic PDF structure"""
        try:
            with open(self.pdf_path, 'rb') as f:
                # Read PDF header
                header = f.read(8)
                self.results['header'] = header.decode('utf-8', errors='ignore')

                # WIP: Check for linearization using a robust regex approach
                f.seek(0)
                first_4096 = f.read(4096)  # Read more bytes for safety
                linearized_regex = re.compile(
                    br'1\s+0\s+obj\s*<<[^>]*?/Linearized[^>]*?>>',
                    re.DOTALL
                )
                self.results['linearized'] = bool(linearized_regex.search(first_4096))

                # Read entire file for analysis
                f.seek(0)
                self.pdf_content = f.read()
                self.results['file_size'] = len(self.pdf_content)

                # Count xref tables (multiple xrefs may indicate modifications)
                xref_count = self.pdf_content.count(b'xref')
                self.results['xref_tables'] = xref_count

        except Exception as e:
            self.results['basic_structure_error'] = str(e)
    
    def _analyze_metadata(self, threshold_days=30):
        """Analyze PDF metadata for inconsistencies"""
        try:
            doc = fitz.open(self.pdf_path)
            metadata = doc.metadata

            self.results['metadata'] = metadata

            # Check for suspicious metadata patterns
            creation_date = metadata.get('creationDate', '')
            mod_date = metadata.get('modDate', '')

            def parse_pdf_date(pdf_date):
                if pdf_date.startswith('D:'):
                    pdf_date = pdf_date[2:16]  # YYYYMMDDHHmmSS
                # Fill missing components with zeros if necessary
                pdf_date = pdf_date.ljust(14, '0')
                try:
                    return datetime.strptime(pdf_date, "%Y%m%d%H%M%S")
                except Exception:
                    return None
                
            # Flag if modification date is before creation date
            if creation_date and mod_date:
                creation_dt = parse_pdf_date(creation_date)
                mod_dt = parse_pdf_date(mod_date)

                if creation_dt and mod_dt:
                    if mod_dt < creation_dt:
                        self.results['metadata_anomaly'] = "Modification date before creation date"
                    else:
                        days_diff = (mod_dt - creation_dt).days
                        if days_diff > threshold_days:
                            self.results['metadata_anomaly'] = (
                                f"Modification date is {days_diff} days after creation date "
                                f"(threshold: {threshold_days} days)"
                            )
                        
            # Check for common editing software signatures
            producer = metadata.get('producer', '').lower()
            creator = metadata.get('creator', '').lower()
            
            suspicious_software = [
                'adobe acrobat', 'foxit', 'nitro', 'pdftk', 'ghostscript',
                'imagemagick', 'libreoffice', 'microsoft print to pdf'
            ]
            
            editing_indicators = []
            for software in suspicious_software:
                if software in producer or software in creator:
                    editing_indicators.append(software)
            
            self.results['potential_editors'] = editing_indicators
            
            # TODO: check each version of the xrefs (records of PDF modification to see if they come from singular or multiple software)

            doc.close()
            
        except Exception as e:
            self.results['metadata_error'] = str(e)
    
    def _analyze_objects(self):
        """Analyze PDF object structure"""
        try:
            # Count different object types
            object_pattern = rb'(\d+)\s+(\d+)\s+obj'
            objects = re.findall(object_pattern, self.pdf_content)
            self.results['total_objects'] = len(objects)
            
            # Look for suspicious object patterns
            # Text objects
            text_objects = self.pdf_content.count(b'/Type/Font') + self.pdf_content.count(b'BT\n')
            self.results['text_objects'] = text_objects
            
            # Image objects
            image_objects = self.pdf_content.count(b'/Type/XObject') + self.pdf_content.count(b'/Subtype/Image')
            self.results['image_objects'] = image_objects
            
            # Form objects (often used in tampering)
            form_objects = self.pdf_content.count(b'/Type/XObject') + self.pdf_content.count(b'/Subtype/Form')
            self.results['form_objects'] = form_objects
            
            # Check for object streams (can hide modifications)
            objstm_count = self.pdf_content.count(b'/Type/ObjStm')
            self.results['object_streams'] = objstm_count
            
        except Exception as e:
            self.results['object_analysis_error'] = str(e)
    
    def _analyze_content_streams(self):
        """Analyze content streams for tampering indicators"""
        try:
            doc = fitz.open(self.pdf_path)
            
            stream_analysis = {
                'pages': len(doc),
                'text_overlays': 0,
                'transparency_groups': 0,
                'unusual_operators': []
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get page content
                content = page.get_contents()
                if content:
                    content_bytes = content[0].get_buffer() if content else b''
                    
                    # Look for text overlay patterns
                    if b'Tm\n' in content_bytes and b'TJ\n' in content_bytes:
                        stream_analysis['text_overlays'] += 1
                    
                    # Look for transparency groups
                    if b'/Type/Group' in content_bytes or b'/S/Transparency' in content_bytes:
                        stream_analysis['transparency_groups'] += 1
                    
                    # Look for unusual graphics operators
                    unusual_ops = [b'ri\n', b'gs\n', b'sh\n']  # Rendering intent, graphics state, shading
                    for op in unusual_ops:
                        if op in content_bytes:
                            stream_analysis['unusual_operators'].append(op.decode('utf-8').strip())
            
            self.results['content_streams'] = stream_analysis
            doc.close()
            
        except Exception as e:
            self.results['content_stream_error'] = str(e)

    def _analyze_fonts(self, unique_fonts_threshold=5):
        """Analyze font usage patterns"""
        try:
            all_fonts_from_text = self._analyze_fonts_from_text()
            
            # Check for mixed font usage (potential tampering indicator)
            unique_fonts = len(all_fonts_from_text)
            self.results['font_analysis'] = {
                'unique_fonts': unique_fonts,
                'font_distribution': dict(all_fonts_from_text),
                'mixed_fonts_flag': unique_fonts > unique_fonts_threshold  # Arbitrary threshold
            }
            
        except Exception as e:
            self.results['font_analysis_error'] = str(e)

    def _analyze_fonts_from_text(self):
        """Alternative method: analyze fonts from text blocks"""
        try:
            doc = fitz.open(self.pdf_path)
            
            all_fonts_from_text = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get text with font information
                blocks = page.get_text("dict")
                
                for block in blocks.get("blocks", []):
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line.get("spans", []):
                                font_name = span.get("font", "Unknown")
                                clean_font = self._clean_font_name(font_name)
                                all_fonts_from_text.append(clean_font)
            
            doc.close()
            return Counter(all_fonts_from_text)
        
        except Exception as e:
            return Counter()

    def _clean_font_name(self, font_name):
        """Remove PDF internal prefixes and extract actual font name"""
        if not font_name:
            return "Unknown"
        
        # Remove PDF subset prefixes (6 uppercase letters + '+')
        cleaned = re.sub(r'^[A-Z]{6}\+', '', font_name)
        
        return cleaned
    
    def _analyze_images(self):
        """Analyze embedded images"""
        try:
            doc = fitz.open(self.pdf_path)
            
            image_analysis = {
                'total_images': 0,
                'image_formats': [],
                'resolution_inconsistencies': []
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    image_analysis['total_images'] += 1
                    
                    # Get image details
                    xref = img[0]
                    try:
                        pix = fitz.Pixmap(doc, xref)
                        image_analysis['image_formats'].append(pix.colorspace.name if pix.colorspace else 'Unknown')
                        
                        # Check for resolution inconsistencies
                        if hasattr(pix, 'width') and hasattr(pix, 'height'):
                            aspect_ratio = pix.width / pix.height if pix.height > 0 else 0
                            if aspect_ratio > 10 or aspect_ratio < 0.1:  # Unusual aspect ratios
                                image_analysis['resolution_inconsistencies'].append(f"Page {page_num+1}, Image {img_index+1}")
                        
                        pix = None
                    except:
                        image_analysis['image_formats'].append('Error')
            
            self.results['image_analysis'] = image_analysis
            doc.close()
            
        except Exception as e:
            self.results['image_analysis_error'] = str(e)
    
    def _analyze_compression(self):
        """Analyze compression patterns"""
        try:
            # Look for different compression methods
            compression_methods = {
                'flate': self.pdf_content.count(b'/Filter/FlateDecode'),
                'ascii85': self.pdf_content.count(b'/Filter/ASCII85Decode'),
                'asciihex': self.pdf_content.count(b'/Filter/ASCIIHexDecode'),
                'lzw': self.pdf_content.count(b'/Filter/LZWDecode'),
                'runlength': self.pdf_content.count(b'/Filter/RunLengthDecode'),
                'ccitt': self.pdf_content.count(b'/Filter/CCITTFaxDecode'),
                'dct': self.pdf_content.count(b'/Filter/DCTDecode')
            }
            
            # Calculate compression ratio estimate
            stream_start = self.pdf_content.count(b'stream\n')
            stream_end = self.pdf_content.count(b'endstream')
            
            self.results['compression_analysis'] = {
                'compression_methods': compression_methods,
                'stream_objects': min(stream_start, stream_end),
                'mixed_compression': sum(1 for v in compression_methods.values() if v > 0) > 2
            }
            
        except Exception as e:
            self.results['compression_error'] = str(e)
    
    def _generate_report(self):
        """Generate forensic analysis report"""
        print("\n📋 FORENSIC ANALYSIS REPORT")
        print("=" * 60)
        
        # Basic file info
        print(f"📄 File Size: {self.results.get('file_size', 0):,} bytes")
        print(f"📑 PDF Version: {self.results.get('header', 'Unknown')}")
        print(f"🔄 XRef Tables: {self.results.get('xref_tables', 0)}")
        print(f"📊 Total Objects: {self.results.get('total_objects', 0)}")
        
        # Metadata analysis
        if 'metadata' in self.results:
            metadata = self.results['metadata']
            print(f"\n📝 Metadata:")
            print(f"   Creator: {metadata.get('creator', 'Unknown')}")
            print(f"   Producer: {metadata.get('producer', 'Unknown')}")
            print(f"   Creation: {metadata.get('creationDate', 'Unknown')}")
            print(f"   Modified: {metadata.get('modDate', 'Unknown')}")
        
        # Tampering indicators
        print(f"\n🚨 TAMPERING INDICATORS:")
        suspicion_score = 0
        
        # Check various indicators
        if self.results.get('xref_tables', 0) > 1:
            print(f"   ⚠️  Multiple XRef tables detected ({self.results['xref_tables']})")
            suspicion_score += 2
        
        if self.results.get('metadata_anomaly'):
            print(f"   ⚠️  Metadata anomaly: {self.results['metadata_anomaly']}")
            suspicion_score += 3
        
        if self.results.get('potential_editors'):
            print(f"   ⚠️  Potential editing software: {', '.join(self.results['potential_editors'])}")
            suspicion_score += 1
        
        if 'content_streams' in self.results:
            cs = self.results['content_streams']
            if cs.get('text_overlays', 0) > 0:
                print(f"   ⚠️  Text overlays detected: {cs['text_overlays']} pages")
                suspicion_score += 2
            
            if cs.get('transparency_groups', 0) > 0:
                print(f"   ⚠️  Transparency groups: {cs['transparency_groups']} pages")
                suspicion_score += 1
        
        if 'font_analysis' in self.results:
            fa = self.results['font_analysis']
            if fa.get('mixed_fonts_flag'):
                print(f"   ⚠️  Unusual font mixing: {fa['unique_fonts']} different fonts")
                suspicion_score += 1
        
        if 'compression_analysis' in self.results:
            ca = self.results['compression_analysis']
            if ca.get('mixed_compression'):
                print(f"   ⚠️  Mixed compression methods detected")
                suspicion_score += 1
        
        # Overall assessment
        print(f"\n🎯 SUSPICION SCORE: {suspicion_score}/10")
        if suspicion_score >= 6:
            risk_level = "HIGH RISK"
            emoji = "🔴"
        elif suspicion_score >= 3:
            risk_level = "MEDIUM RISK"
            emoji = "🟡"
        else:
            risk_level = "LOW RISK"
            emoji = "🟢"
        
        print(f"{emoji} RISK LEVEL: {risk_level}")

if __name__ == "__main__":
    import sys
    import os

    print("PDF Forensic Structure Analyzer")
    if len(sys.argv) < 2:
        print("⚠️  Please provide a PDF file path.")
        print("Usage: python tamper.py <your_document.pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"⚠️  File not found: {pdf_path}")
        sys.exit(1)

    analyzer = PDFForensicAnalyzer(pdf_path)
    analyzer.analyze_file_structure()