import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Any, Set
from datetime import datetime
import os
import pickle
from tqdm import tqdm
from copy import deepcopy

class PDFProcessor:
    def __init__(self, model_name="mistral"):
        self.model_name = model_name
        ################
        #LOCAL ollama MODEL SERVED at PORT 11434
        #################
        self.base_url = "http://localhost:11434"
        ######
        #OUTPUT FOLDER NAME BELOW
        #######
        self.output_dir = Path("output_v4")
        self.output_dir.mkdir(exist_ok=True)
        ########
        ### LOGIC TO SAVE CHECKPOINT TO RESTART RUN IF FAILED 
        ########
        self.checkpoint_file = "processing_checkpoint_v4.pkl"
        self.processed_sections = self.load_checkpoint()
        self.session = requests.Session()

    def load_checkpoint(self) -> Set[str]:
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'rb') as f:
                    checkpoint = pickle.load(f)
                return checkpoint
            except Exception as e:
                return set()
        return set()

    def save_checkpoint(self, filename: str, keyword: str):
        key = f"{filename}|{keyword}"
        self.processed_sections.add(key)
        with open(self.checkpoint_file, 'wb') as f:
            pickle.dump(self.processed_sections, f)

    def generate_narrative(self, filename: str, keyword: str, occurrences: List[Dict]) -> str:
        pages = set()
        contents = []
        for occurrence in occurrences:
            pages.add(occurrence.get('page', 0))
            content = occurrence.get('content', '')
            if content:
                contents.append(content)

        ##################
        ### BASE PROMPT STARTS HERE
        ##################

        prompt = f"""Transform this insurance policy information into a concise summary of 5-10 sentences maximum, presented as a single flowing paragraph. Prioritize the most important information while maintaining accuracy.

        Document: {filename}
        Keyword: {keyword}
        Page Numbers: {sorted(pages)}

        Content to transform:
        {' '.join(contents)}

        Important notes:
        - Create a single flowing paragraph of 5-10 sentences only
        - For longer sections, focus on the most crucial details and requirements
        - Present information in natural sentence flow without any formatting
        - Combine related points into single, well-constructed sentences
        - Include critical dates, numbers, and percentages
        - Maintain technical terms but integrate them naturally
        - No bullet points, line breaks, or structured formatting
        - No introductory phrases like "this section covers" or "there are several requirements"

        Begin the paragraph with: This information comes from {filename} found on pages {sorted(pages)} which explains"""



        ##################
        ### BASE PROMPT ENDS HERE
        ##################

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
            
            if response.status_code == 200:
                narrative = response.json()['response'].strip()
                return narrative
            else:
                return None
        except Exception as e:
            return None

   #########################
   ### PROCESSING LOGIC FOR output_v3.json generated after running pdf-extract-3.py
   ############################
    def process_json_file(self, json_path: str):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        combined_narratives_text = []
        combined_narratives_json = {}
        
        for filename, keywords in tqdm(data.items(), desc="Processing files"):
            file_narratives = []
            file_narratives_json = {}
            
            file_output_path_txt = self.output_dir / f"{filename.replace('.pdf', '_narratives.txt')}"
            file_output_path_json = self.output_dir / f"{filename.replace('.pdf', '_narratives.json')}"
            
            file_narratives_json[filename] = {}
            
            for keyword, occurrences in keywords.items():
                checkpoint_key = f"{filename}|{keyword}"
                
                if checkpoint_key in self.processed_sections:
                    continue
                
                if occurrences:
                    narrative = self.generate_narrative(filename, keyword, occurrences)
                    if narrative:
                        file_narratives.append(narrative)
                        
                        file_narratives_json[filename][keyword] = []
                        for occurrence in occurrences:
                            new_occurrence = deepcopy(occurrence)
                            new_occurrence['narrative'] = narrative
                            file_narratives_json[filename][keyword].append(new_occurrence)
                        
                        self.save_checkpoint(filename, keyword)
            
            if file_narratives:
                with open(file_output_path_txt, 'w', encoding='utf-8') as f:
                    f.write("\n<EOS>\n".join(file_narratives))
                
                with open(file_output_path_json, 'w', encoding='utf-8') as f:
                    json.dump(file_narratives_json, f, indent=2, ensure_ascii=False)
                
                combined_narratives_text.extend(file_narratives)
                combined_narratives_json.update(file_narratives_json)
        
        combined_output_path_txt = self.output_dir / "combined_narratives.txt"
        combined_output_path_json = self.output_dir / "combined_narratives.json"
        
        with open(combined_output_path_txt, 'w', encoding='utf-8') as f:
            f.write("\n<EOS>\n".join(combined_narratives_text))
            
        with open(combined_output_path_json, 'w', encoding='utf-8') as f:
            json.dump(combined_narratives_json, f, indent=2, ensure_ascii=False)

def main():
    processor = PDFProcessor()

    ###################
    ### CHANGE THE FILENAME OUTPUTTED FROM RUNNING THE pdf-extract-3.py file
    ##################
    processor.process_json_file("output_v3.json")

if __name__ == "__main__":
    main()