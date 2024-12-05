import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Any, Set
from datetime import datetime
import os
import pickle
from tqdm import tqdm
import logging

class PDFProcessor:
    def __init__(self, model_name="mistral"):
        self.model_name = model_name
        self.base_url = "http://localhost:11434"
        self.output_dir = Path("output_v3")
        self.output_dir.mkdir(exist_ok=True)
        self.checkpoint_file = "processing_checkpoint_v3.pkl"
        self.processed_sections = self.load_checkpoint()
        self.session = requests.Session()
        
        #log formatting for later time
        # logging.basicConfig(
        #     level=logging.INFO,
        #     format='%(asctime)s - %(levelname)s - %(message)s',
        #     handlers=[
        #         logging.FileHandler('processing_v3.log'),
        #         logging.StreamHandler()
        #     ]
        # )
        # self.logger = logging.getLogger(__name__)

    def load_checkpoint(self) -> Set[str]:
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'rb') as f:
                    checkpoint = pickle.load(f)
                return checkpoint
            except Exception as e:
                return set()
        return set()

    def save_checkpoint(self, filename: str, section_name: str):
        key = f"{filename}|{section_name}"
        self.processed_sections.add(key)
        with open(self.checkpoint_file, 'wb') as f:
            pickle.dump(self.processed_sections, f)

    def generate_narrative(self, filename: str, section_data: Dict) -> str:
        section_name = section_data.get('section', '')
        content = section_data.get('content', '')
        metadata = section_data.get('metadata', {})
        

        ########################
        #BASE PROMPT SECTION STARTS
        ########################
        
        prompt = f"""Transform this insurance policy section into a concise summary of 5-10 sentences maximum, presented as a single flowing paragraph. Prioritize the most important information while maintaining accuracy.

        Document: {filename}
        Section: {section_name}
        Page Numbers: {metadata.get('page_numbers', [])}
        Row Numbers: {metadata.get('row_numbers', [])}

        Content to transform:
        {content}

        Important notes:
        - Create a single flowing paragraph of 5-10 sentences only
        - For longer sections, focus on the most crucial details and requirements
        - Present information in natural sentence flow without any formatting
        - Combine related points into single, well-constructed sentences
        - Include critical dates, numbers, and percentages
        - Maintain technical terms but integrate them naturally
        - No bullet points, line breaks, or structured formatting
        - No introductory phrases like "this section covers" or "there are several requirements"

        Begin the paragraph with: This information comes from {filename} page numbers {metadata.get('page_numbers', [])} rows {metadata.get('row_numbers', [])} which explains"""


        #########################
        #BASE PROMPT SECTION ENDS
        #########################

        try:
            start_time = time.time()
            
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "temperature": 0.3,
                    "stream": False
                },
                timeout=90
            )
            
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                narrative = response.json()['response'].strip()
                return narrative
            else:
                return None
        except Exception as e:
            return None

    def process_json_file(self, json_path: str):
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total_files = len(data)
        
        for file_num, (filename, sections) in enumerate(tqdm(data.items(), desc="Processing files")):
            file_narratives = []
            total_sections = len(sections)
            
            file_output_path = self.output_dir / f"{filename.replace('.pdf', '_narratives.txt')}"
            
            for section_num, (section_name, section_data) in enumerate(sections.items(), 1):
                
                checkpoint_key = f"{filename}|{section_name}"
    
                if checkpoint_key in self.processed_sections:
                    continue
                
                narrative = self.generate_narrative(filename, {
                    'section': section_name,
                    'content': section_data['content'],
                    'metadata': section_data['metadata']
                })
                
                if narrative:
                    file_narratives.append(narrative)
                    self.save_checkpoint(filename, section_name)
                else:
                    pass
            
            if file_narratives:
                with open(file_output_path, 'w', encoding='utf-8') as f:
                    f.write("\n<EOS>\n".join(file_narratives))
            
            combined_output_path = self.output_dir / "combined_narratives.txt"
            with open(combined_output_path, 'a', encoding='utf-8') as f:
                f.write("\n<EOS>\n".join(file_narratives))
                f.write("\n<EOS>\n\n")

def main():
    processor = PDFProcessor()
    ### JSON FILE GENERATED FROM 
    processor.process_json_file("pdf_structure_20241204_001823.json")

if __name__ == "__main__":
    main()