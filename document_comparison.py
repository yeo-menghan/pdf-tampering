import fitz  # PyMuPDF
import sqlite3
import re
import json
from datetime import datetime
from difflib import SequenceMatcher
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

@dataclass
class DocumentData:
    """Standardized document data structure"""
    vendor: str
    client: str
    date: Optional[str]
    postal_code: str
    items: List[Dict[str, Any]]
    total: float
    signatory: str
    document_type: str = "quotation"
    reference_number: str = ""
    additional_fields: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_fields is None:
            self.additional_fields = {}

class DocumentParser(ABC):
    """Abstract base class for document parsers"""
    
    @abstractmethod
    def parse(self, text: str) -> DocumentData:
        pass
    
    @abstractmethod
    def get_document_type(self) -> str:
        pass

class QuotationParser(DocumentParser):
    """Parser for quotation documents"""
    
    def parse(self, text: str) -> DocumentData:
        vendor = re.search(r'(?P<vendor>[A-Z][A-Z\s&]+PTE LTD)', text)
        client = re.search(r'Lian Soon Construction Pte Ltd', text)
        date = re.search(r'(\d{1,2} [A-Za-z]+ 20\d{2})', text)
        postal_code = re.search(r'Singapore (\d{6})', text)
        signatory = re.search(r'(?i)Name:\s*(.*)\n', text)
        total = re.search(r'TOTAL AMT?:\s*\$?([0-9,]+\.\d{2})', text.replace(",", ""))
        ref_number = re.search(r'(?i)(?:ref|quote|quotation)[\s#]*:?\s*([A-Z0-9-]+)', text)
        
        # Extract items
        items = []
        item_lines = re.findall(r'(\d+)[\s\t]+([A-Za-z \'()]+)[\s\t]+(\d+)[\s\t]+nos[\s\t]+\$?([\d.]+)[\s\t]+\$?([\d.]+)', text)
        for line in item_lines:
            qty, name, qty2, rate, total_item = line
            items.append({
                "name": name.strip(),
                "qty": int(qty),
                "rate": float(rate),
                "total": float(total_item)
            })
        
        return DocumentData(
            vendor=vendor.group("vendor") if vendor else "Unknown Vendor",
            client=client.group(0) if client else "Unknown Client",
            date=datetime.strptime(date.group(1), "%d %B %Y").strftime("%Y-%m-%d") if date else None,
            postal_code=postal_code.group(1) if postal_code else "",
            items=items,
            total=float(total.group(1)) if total else 0.0,
            signatory=signatory.group(1).strip() if signatory else "",
            document_type=self.get_document_type(),
            reference_number=ref_number.group(1) if ref_number else ""
        )
    
    def get_document_type(self) -> str:
        return "quotation"

class ContractParser(DocumentParser):
    """Parser for contract documents"""
    
    def parse(self, text: str) -> DocumentData:
        # Similar parsing logic but adapted for contracts
        vendor = re.search(r'(?i)contractor:\s*([A-Z][A-Za-z\s&]+(?:PTE LTD|LTD|INC))', text)
        client = re.search(r'(?i)client:\s*([A-Z][A-Za-z\s&]+(?:PTE LTD|LTD|INC))', text)
        date = re.search(r'(?i)date:\s*(\d{1,2}[\/\-][A-Za-z0-9]+[\/\-]20\d{2})', text)
        postal_code = re.search(r'Singapore (\d{6})', text)
        signatory = re.search(r'(?i)(?:signed|signature):\s*(.*)\n', text)
        total = re.search(r'(?i)(?:contract|total)\s*(?:value|amount):\s*\$?([0-9,]+\.\d{2})', text.replace(",", ""))
        contract_number = re.search(r'(?i)contract[\s#]*:?\s*([A-Z0-9-]+)', text)
        
        # Extract contract items/clauses
        items = []
        # This would need to be customized based on contract format
        
        return DocumentData(
            vendor=vendor.group(1) if vendor else "Unknown Contractor",
            client=client.group(1) if client else "Unknown Client",
            date=date.group(1) if date else None,
            postal_code=postal_code.group(1) if postal_code else "",
            items=items,
            total=float(total.group(1)) if total else 0.0,
            signatory=signatory.group(1).strip() if signatory else "",
            document_type=self.get_document_type(),
            reference_number=contract_number.group(1) if contract_number else ""
        )
    
    def get_document_type(self) -> str:
        return "contract"

@dataclass
class SimilarityConfig:
    """Configuration for similarity detection thresholds"""
    address_threshold: float = 0.8
    items_threshold: float = 0.8
    price_difference_threshold: float = 0.1
    days_threshold: int = 3
    text_similarity_threshold: float = 0.9
    signatory_exact_match: bool = True

class DocumentFraudDetector:
    """Main class for detecting potential document fraud"""
    
    def __init__(self, db_path: str = 'documents.db', config: SimilarityConfig = None):
        self.db_path = db_path
        self.config = config or SimilarityConfig()
        self.parsers = {
            'quotation': QuotationParser(),
            'contract': ContractParser()
        }
        self.setup_db()
    
    def setup_db(self):
        """Setup database with enhanced schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_type TEXT,
                vendor TEXT,
                client TEXT,
                date TEXT,
                postal_code TEXT,
                items TEXT,
                total REAL,
                signatory TEXT,
                reference_number TEXT,
                additional_fields TEXT,
                raw_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    
    def detect_document_type(self, text: str) -> str:
        """Auto-detect document type based on content"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['quotation', 'quote', 'estimate']):
            return 'quotation'
        elif any(word in text_lower for word in ['contract', 'agreement', 'terms']):
            return 'contract'
        else:
            return 'quotation'  # default
    
    def parse_document(self, text: str, document_type: str = None) -> DocumentData:
        """Parse document using appropriate parser"""
        if document_type is None:
            document_type = self.detect_document_type(text)
        
        parser = self.parsers.get(document_type)
        if not parser:
            raise ValueError(f"No parser available for document type: {document_type}")
        
        return parser.parse(text)
    
    def insert_document(self, data: DocumentData, raw_text: str):
        """Insert document into database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO documents (document_type, vendor, client, date, postal_code, 
                                 items, total, signatory, reference_number, 
                                 additional_fields, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.document_type, data.vendor, data.client, data.date, 
            data.postal_code, json.dumps(data.items), data.total, 
            data.signatory, data.reference_number, 
            json.dumps(data.additional_fields), raw_text
        ))
        conn.commit()
        last_id = c.lastrowid
        conn.close()
        return last_id
    
    def fetch_existing_documents(self, exclude_id: int = None, document_type: str = None) -> List[Tuple]:
        """Fetch existing documents for comparison"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        query = """
            SELECT id, document_type, vendor, client, date, postal_code, 
                   items, total, signatory, reference_number, additional_fields, raw_text
            FROM documents
        """
        params = []
        
        conditions = []
        if exclude_id:
            conditions.append("id != ?")
            params.append(exclude_id)
        if document_type:
            conditions.append("document_type = ?")
            params.append(document_type)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        c.execute(query, params)
        results = c.fetchall()
        conn.close()
        return results
    
    def text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using sequence matcher"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def address_similarity(self, addr1: str, addr2: str) -> float:
        """Calculate address similarity"""
        return SequenceMatcher(None, addr1, addr2).ratio()
    
    def items_similarity(self, items1: List[Dict], items2: List[Dict]) -> float:
        """Calculate items similarity"""
        if not items1 or not items2:
            return 0.0
        
        set1 = set((item.get('name', '').lower(), item.get('qty', 0)) for item in items1)
        set2 = set((item.get('name', '').lower(), item.get('qty', 0)) for item in items2)
        
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / len(union)
    
    def price_difference(self, total1: float, total2: float) -> float:
        """Calculate relative price difference"""
        if total1 == 0 and total2 == 0:
            return 0.0
        if total1 == 0 or total2 == 0:
            return 1.0
        return abs(total1 - total2) / max(total1, total2)
    
    def date_difference(self, date1: str, date2: str) -> int:
        """Calculate difference in days between dates"""
        if not date1 or not date2:
            return float('inf')
        try:
            d1 = datetime.strptime(date1, "%Y-%m-%d")
            d2 = datetime.strptime(date2, "%Y-%m-%d")
            return abs((d1 - d2).days)
        except ValueError:
            return float('inf')
    
    def detect_fraud_indicators(self, new_doc: DocumentData, raw_text: str, 
                              existing_docs: List[Tuple]) -> List[Dict]:
        """Detect potential fraud indicators"""
        flags = []
        
        for row in existing_docs:
            (doc_id, doc_type, vendor, client, date, postal_code, 
             items_json, total, signatory, ref_number, additional_fields, existing_text) = row
            
            issues = []
            risk_score = 0
            
            try:
                items_existing = json.loads(items_json) if items_json else []
            except json.JSONDecodeError:
                items_existing = []
            
            # Text similarity check
            text_sim = self.text_similarity(raw_text, existing_text)
            if text_sim > self.config.text_similarity_threshold:
                issues.append(f"Very high text similarity: {text_sim:.3f}")
                risk_score += 50
            
            # Address/postal code check
            # TODO: use fuzzy matching for addresses
            if (new_doc.postal_code and postal_code and 
                new_doc.postal_code != postal_code):
                addr_sim = self.address_similarity(new_doc.postal_code, postal_code)
                if addr_sim > self.config.address_threshold:
                    issues.append(f"Similar but different addresses: {addr_sim:.3f}")
                    risk_score += 20
            
            # Items similarity
            # TODO: use fuzzy matching for item names
            item_sim = self.items_similarity(new_doc.items, items_existing)
            if item_sim > self.config.items_threshold:
                issues.append(f"High item similarity: {item_sim:.3f}")
                risk_score += 30
                
                # Price difference for similar items
                price_diff = self.price_difference(new_doc.total, total)
                if price_diff > self.config.price_difference_threshold:
                    issues.append(f"Significant price difference for similar items: {price_diff*100:.1f}%")
                    risk_score += 25
            
            # Date proximity
            days_apart = self.date_difference(new_doc.date, date)
            if days_apart <= self.config.days_threshold:
                issues.append(f"Documents submitted within {days_apart} days")
                risk_score += 15
            
            # Same signatory, different vendor
            if (new_doc.vendor != vendor and new_doc.signatory and 
                new_doc.signatory == signatory and self.config.signatory_exact_match):
                issues.append(f"Same signatory '{signatory}' for different vendors")
                risk_score += 40
            
            # Reference number duplication
            if (new_doc.reference_number and ref_number and 
                new_doc.reference_number == ref_number):
                issues.append(f"Duplicate reference number: {ref_number}")
                risk_score += 35
            
            if issues:
                flags.append({
                    'existing_doc_id': doc_id,
                    'existing_vendor': vendor,
                    'existing_type': doc_type,
                    'risk_score': risk_score,
                    'issues': issues
                })
        
        # Sort by risk score (highest first)
        flags.sort(key=lambda x: x['risk_score'], reverse=True)
        return flags
    
    def process_document(self, pdf_path: str, document_type: str = None) -> Dict:
        """Main processing function"""
        # Extract and parse
        raw_text = self.extract_text_from_pdf(pdf_path)
        doc_data = self.parse_document(raw_text, document_type)
        
        # Insert into database
        doc_id = self.insert_document(doc_data, raw_text)
        
        # Get existing documents for comparison
        existing_docs = self.fetch_existing_documents(
            exclude_id=doc_id, 
            document_type=doc_data.document_type
        )
        
        # Detect fraud indicators
        flags = self.detect_fraud_indicators(doc_data, raw_text, existing_docs)
        
        return {
            'document_id': doc_id,
            'document_data': asdict(doc_data),
            'flags': flags,
            'risk_assessment': self._assess_overall_risk(flags)
        }
    
    def _assess_overall_risk(self, flags: List[Dict]) -> Dict:
        """Assess overall risk level"""
        if not flags:
            return {'level': 'LOW', 'score': 0, 'description': 'No suspicious patterns detected'}
        
        max_score = max(flag['risk_score'] for flag in flags)
        
        if max_score >= 80:
            level = 'CRITICAL'
            description = 'High probability of document fraud detected'
        elif max_score >= 60:
            level = 'HIGH'
            description = 'Multiple suspicious indicators detected'
        elif max_score >= 40:
            level = 'MEDIUM'
            description = 'Some suspicious patterns detected'
        else:
            level = 'LOW'
            description = 'Minor similarities detected'
        
        return {
            'level': level,
            'score': max_score,
            'description': description,
            'flagged_documents': len(flags)
        }

def main():
    """Main function with enhanced reporting"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fraud_detector.py <PDF1> [PDF2 ...] [--config config.json]")
        sys.exit(1)
    
    # Initialize detector
    config = SimilarityConfig()  # You can load from JSON file
    detector = DocumentFraudDetector(config=config)
    
    for pdf_file in sys.argv[1:]:
        if pdf_file.startswith('--'):
            continue
            
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file}")
        print('='*60)
        
        try:
            result = detector.process_document(pdf_file)
            doc_data = result['document_data']
            risk = result['risk_assessment']
            
            print(f"Document Type: {doc_data['document_type']}")
            print(f"Vendor: {doc_data['vendor']}")
            print(f"Total: ${doc_data['total']:.2f}")
            print(f"Date: {doc_data['date']}")
            
            print(f"\nRisk Assessment: {risk['level']} (Score: {risk['score']})")
            print(f"Description: {risk['description']}")
            
            if result['flags']:
                print(f"\nDetailed Findings:")
                for i, flag in enumerate(result['flags'][:3], 1):  # Show top 3
                    print(f"\n{i}. Comparison with Document ID {flag['existing_doc_id']} "
                          f"({flag['existing_vendor']}) - Risk Score: {flag['risk_score']}")
                    for issue in flag['issues']:
                        print(f"   • {issue}")
            else:
                print("\nNo suspicious patterns detected.")
                
        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}")

if __name__ == "__main__":
    main()