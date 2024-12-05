#!/usr/bin/env python3

import fitz
import json
from pathlib import Path
import re
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor
import argparse
import sys
from datetime import datetime


class PDFReader:
    def __init__(self):
        self.header_patterns = {
            'numbered': r'^[0-9]+\.[0-9]*\s+[A-Z]',
            'uppercase': r'^[A-Z][A-Z\s]{4,}',
            'titlecase': r'^[A-Z][a-z]+(\s+[A-Z][a-z]+){0,3}$'
        }
    
    def is_header(self, text: str, font_info: Dict) -> bool:
        text = text.strip()
        if not text:
            return False
            
        return (any(re.match(pattern, text) for pattern in self.header_patterns.values()) or
                font_info['size'] > 12 or 
                font_info['flags'] & 16)
    
    # def has_meaningful_content(self, text: str) -> bool:
    #     cleaned_text = text.strip()
    #     if not cleaned_text:
    #         return False
    #     if len(cleaned_text) <= 1 or cleaned_text.isspace():
    #         return False
    #     return True
    
    ##########################
    #MAIN PDF PROCESSING FILE
    ###########################
    def process_single_pdf(self, pdf_path: str) -> Dict:
        doc = fitz.open(pdf_path)
        sections = {}
        current_section = "Introduction"
        current_block = []
        current_metadata = {
            'page_numbers': set(),
            'row_numbers': [],
            'text_blocks': []
        }
        
        try:
            for page_num, page in enumerate(doc, 1):
                blocks = page.get_text("dict")["blocks"]
                
                for block_num, block in enumerate(blocks):
                    if "lines" not in block:
                        continue
                    
                    for line_num, line in enumerate(block["lines"], 1):
                        spans = line["spans"]
                        if not spans:
                            continue
                            
                        text = " ".join(span["text"] for span in spans).strip()
                        
                        if not self.has_meaningful_content(text):
                            continue
                        
                        font_info = {
                            'size': spans[0].get('size', 0),
                            'flags': spans[0].get('flags', 0)
                        }
                        
                        if self.is_header(text, font_info):
                            if current_block:
                                sections[current_section] = {
                                    'content': " ".join(current_block),
                                    'metadata': {
                                        'page_numbers': sorted(current_metadata['page_numbers']),
                                        'row_numbers': current_metadata['row_numbers'],
                                        'text_blocks': current_metadata['text_blocks']
                                    }
                                }
                                current_block = []
                                current_metadata = {
                                    'page_numbers': set(),
                                    'row_numbers': [],
                                    'text_blocks': []
                                }
                            current_section = text
                        else:
                            current_block.append(text)
                            current_metadata['page_numbers'].add(page_num)
                            current_metadata['row_numbers'].append(line_num)
                            current_metadata['text_blocks'].append({
                                'text': text,
                                'page': page_num,
                                'row': line_num,
                                'block': block_num
                            })
            
            if current_block:
                sections[current_section] = {
                    'content': " ".join(current_block),
                    'metadata': {
                        'page_numbers': sorted(current_metadata['page_numbers']),
                        'row_numbers': current_metadata['row_numbers'],
                        'text_blocks': current_metadata['text_blocks']
                    }
                }
                
        finally:
            doc.close()
        
        sections = {k: v for k, v in sections.items() 
                   if self.has_meaningful_content(v['content'])}
            
        return sections
    
    def process_pdf_folder(self, folder_path: str, output_path: str, 
                          max_workers: Optional[int] = None) -> None:
        folder = Path(folder_path)
        pdf_files = list(folder.glob('*.pdf'))
        
        if not pdf_files:
            raise ValueError(f"No PDF files found in {folder_path}")
        
        combined_structure = {}
        
        #############
        #TEMPLATE FOR THREADPOOL FOR FASTER PROCESSING FOR MORE PDF LATER
        #####################

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self.process_single_pdf, str(pdf_path)): pdf_path
                for pdf_path in pdf_files
            }
            
            for future in future_to_path:
                pdf_path = future_to_path[future]
                try:
                    result = future.result()
                    combined_structure[pdf_path.name] = result
                    print(f"Processed: {pdf_path.name}")
                    
                    for section_name, section_data in result.items():
                        if self.has_meaningful_content(section_data['content']):
                            print(f"Section: {section_name}")
                            print(f"Pages: {section_data['metadata']['page_numbers']}")
                            print(f"Total rows: {len(section_data['metadata']['row_numbers'])}")
                        
                except Exception as e:
                    print(f"Error processing {pdf_path.name}: {str(e)}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(combined_structure, indent=2, ensure_ascii=False, fp=f)
        
        print(f"Output saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Extract structured content from PDFs')
    parser.add_argument('input_folder', help='Folder containing PDF files')
    parser.add_argument(
        '--output', '-o',
        default=f'pdf_structure_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
    )

    args = parser.parse_args()

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
