import fitz
import json
from pathlib import Path
from typing import Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor
import argparse
import sys
from datetime import datetime

class PDFReader:
    def __init__(self):
        ######
        #THESE KEYWORDS COME FROM THE EXCEL FILE FORMAT REQUESTED
        #######
        self.keywords = {
            'Carrier',
            'Effective Date',
            'State', 
            'Minimum Hours Requirement',
            'Waiting Period', 'Rehire Provision',
            'Contribution',
            'Elimination Period',
            'Benefit Percentage',
            'Maximum Benefit', 
            'Maximum Duration',
            'Minimum Benefit',
            'Rehabilitation Benefit', 
            'Dependent Care Expense Benefit',
            'Continuity of Coverage',
            'Pre-existing Condition',
            'Survivor Benefit',
            'Work Life Assistance Program',
            'Waiver of Premium',
            'Own Occupation Period',
            'Own Occupation Definition',
            'Own Occupation %', 
            'Own Occupation Indexed Income?',
            'Gainful Occupation Definition',
            'Gainful Occupation %',
            'Gainful Occupation Indexed Income?',
            'Trial Work Period',
            'Monthly Earnings',
            'Total Disability Threshold',
            'RTW Incentive',
            'Partial Disability Formula',
            'Self-reported Condition Limitation',
            'Mental Illness Limitation',
            'Recurrent Disability Period',
            'Survivor Benefit',
            'Worksite Modification',
            'Maximum Capacity Language',
            '40-hour Capacity Cap'
        }

    #####
    #CHECK FOR ANY HEADER SECTION BASED ON FONT IN PDF
    #####
    def is_header(self, text: str, spans) -> bool:
        if not text:
            return False
        return (text.isupper() or 
                text.rstrip().endswith(':') or
                spans[0].get('size', 0) > 12 or 
                spans[0].get('flags', 0) & 16)

    ########
    ## GET ALL THE SECTION CONTENT FOR THAT IDENTIFIED SECTION
    #######
    def extract_section_content(self, blocks: List, start_idx: int, page_num: int) -> str:
        content = []
        current_idx = start_idx
        
        while current_idx < len(blocks):
            block = blocks[current_idx]
            if "lines" not in block:
                current_idx += 1
                continue
                
            for line in block["lines"]:
                if not line.get("spans"):
                    continue
                    
                text = " ".join(span["text"] for span in line["spans"]).strip()
                if not text:
                    continue
                    
                ###
                ## NEEDS TWEAKS FRO STOPPING BEFORE ANOTHER HEADER IS SEEN
                ####
                if current_idx != start_idx and self.is_header(text, line["spans"]):
                    return " ".join(content)
                
                content.append(text)
            current_idx += 1
        
        return " ".join(content)

    def process_single_pdf(self, pdf_path: str) -> Dict:
        doc = fitz.open(pdf_path)
        findings = {}
        
        try:
            for page_num, page in enumerate(doc, 1):
                blocks = page.get_text("dict")["blocks"]
                
                for block_num, block in enumerate(blocks):
                    if "lines" not in block:
                        continue
                    
                    for line_num, line in enumerate(block["lines"], 1):
                        if not line.get("spans"):
                            continue
                            
                        text = " ".join(span["text"] for span in line["spans"]).strip()
                        
                        ######
                        ## KEYWORD MAPPING LOGIC
                        ######
                        for keyword in self.keywords:
                            if keyword.lower() in text.lower():
                                section_content = self.extract_section_content(blocks, block_num, page_num)
                                
                                if keyword not in findings:
                                    findings[keyword] = []
                                    
                                findings[keyword].append({
                                    'page': page_num,
                                    'line': line_num,
                                    'selected_text': text,
                                    'content': section_content
                                })
                            
        finally:
            doc.close()
            
        return findings
    
    def process_pdf_folder(self, folder_path: str, output_path: str, 
                          max_workers: Optional[int] = None) -> None:
        folder = Path(folder_path)
        pdf_files = list(folder.glob('*.pdf'))
        
        if not pdf_files:
            raise ValueError(f"No PDF files found in {folder_path}")
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self.process_single_pdf, str(pdf_path)): pdf_path
                for pdf_path in pdf_files
            }
            
            for future in future_to_path:
                pdf_path = future_to_path[future]
                try:
                    filename = pdf_path.name
                    findings = future.result()
                    
                    if findings:
                        results[filename] = findings
                        print(f"\nProcessed: {filename}")
                        for keyword, matches in findings.items():
                            print(f"Found '{keyword}' in {len(matches)} locations:")
                            for match in matches:
                                print(f"  Page {match['page']}, Line: {match['line']}")
                        
                except Exception as e:
                    print(f"Error processing {pdf_path.name}: {str(e)}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nOutput saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Extract sections with keywords from PDFs')
    parser.add_argument('input_folder', help='Folder containing PDF files')
    parser.add_argument(
        '--output', '-o',
        default=f'pdf_findings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        help='Output JSON file path'
    )

    args = parser.parse_args()

    ########
    ###TO RUN - pass arguments as python3 <filename>.py <input_folder> --output <output_json_file_name>
    #########

    try:
        extractor = PDFReader()
        extractor.process_pdf_folder(
            folder_path=args.input_folder,
            output_path=args.output,
        )
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()