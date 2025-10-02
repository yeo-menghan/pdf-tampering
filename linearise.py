import subprocess

def linearize_pdf(input_path, output_path):
    try:
        subprocess.run(['qpdf', '--linearize', input_path, output_path], check=True)
        print(f"Linearized PDF saved as {output_path}")
    except Exception as e:
        print(f"Error linearizing PDF: {e}")

# Example usage:
linearize_pdf('./sample-data/hi.pdf', './sample-data/output_linearized.pdf')