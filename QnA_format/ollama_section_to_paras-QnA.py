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
        self.base_url = "http://localhost:11434"
        self.output_dir = Path("output_QnA")
        self.output_dir.mkdir(exist_ok=True)
        self.checkpoint_file = "processing_checkpoint_QnA.pkl"
        self.processed_sections = self.load_checkpoint()
        self.session = requests.Session()
        self.keywords = {
            'Carrier', 'Effective Date', 'State', 
            'Minimum Hours Requirement', 'Waiting Period', 'Rehire Provision',
            'Contribution', 'Elimination Period', 'Benefit Percentage',
            'Maximum Benefit', 'Maximum Duration', 'Minimum Benefit',
            'Rehabilitation Benefit', 'Dependent Care Expense Benefit',
            'Continuity of Coverage', 'Pre-existing Condition', 'Survivor Benefit',
            'Work Life Assistance Program', 'Waiver of Premium',
            'Own Occupation Period', 'Own Occupation Definition',
            'Own Occupation %', 'Own Occupation Indexed Income?',
            'Gainful Occupation Definition', 'Gainful Occupation %',
            'Gainful Occupation Indexed Income?', 'Trial Work Period',
            'Monthly Earnings', 'Total Disability Threshold',
            'RTW Incentive', 'Partial Disability Formula',
            'Self-reported Condition Limitation', 'Mental Illness Limitation',
            'Recurrent Disability Period', 'Survivor Benefit',
            'Worksite Modification', 'Maximum Capacity Language',
            '40-hour Capacity Cap'
        }

    def load_checkpoint(self) -> Set[str]:
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error loading checkpoint: {e}")
                return set()
        return set()

    def save_checkpoint(self, filename: str, keyword: str):
        try:
            key = f"{filename}|{keyword}"
            self.processed_sections.add(key)
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump(self.processed_sections, f)
        except Exception as e:
            print(f"Error saving checkpoint: {e}")

    def parse_qa_response(self, response_text: str) -> List[Dict[str, str]]:
        qa_pairs = []
        try:
            lines = [line.strip() for line in response_text.split('\n') if line.strip()]
            
            current_q = None
            current_a = None
            
            for line in lines:
                if line.startswith(('Q:', 'Q1:', 'Q2:', 'Q3:')):
                    if current_q and current_a:
                        qa_pairs.append({
                            'question': current_q,
                            'answer': current_a
                        })
                    current_q = line.split(':', 1)[1].strip().strip('"')
                    current_a = None
                elif line.startswith(('A:', 'A1:', 'A2:', 'A3:')):
                    current_a = line.split(':', 1)[1].strip().strip('"')
            
            if current_q and current_a:
                qa_pairs.append({
                    'question': current_q,
                    'answer': current_a
                })
                
        except Exception as e:
            print(f"Error parsing QA response: {e}")
            return []
            
        return qa_pairs

    def generate_qa_pairs(self, filename: str, keyword: str, occurrences: List[Dict]) -> List[Dict]:
        if not occurrences:
            return []
            
        try:
            pages = set()
            contents = []
            for occurrence in occurrences:
                if 'page' in occurrence:
                    pages.add(occurrence['page'])
                content = occurrence.get('content', '').strip()
                if content:
                    contents.append(content)

            if not contents:
                return []

            prompt = f"""Generate 2-3 question-answer pairs about {keyword} based on the provided content. Focus on specific policy details, requirements, or conditions.

            Document: {filename}
            Keyword: {keyword}
            Page Numbers: {sorted(pages)}

            Content:
            {' '.join(contents)}

            Rules for questions:
            - Make questions specific and focused on key policy details
            - Use direct, single-line questions
            - Ask about dates, percentages, requirements, or conditions mentioned

            Rules for answers:
            - Start each answer with "Based on {filename} page {sorted(pages)}"
            - Keep answers in a single flowing paragraph
            - Include specific numbers, dates, percentages as mentioned
            - Be technical and precise
            - No bullet points or structured formatting
            - No filler phrases or unnecessary explanations

            Format each Q&A pair as:
            Q1: "specific question here?"
            A1: "technical answer here"
            Q2: "next question here?"
            A2: "technical answer here"
            Q3: "final question here?"
            A3: "technical answer here"
            """

            max_retries = 3
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
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
                        qa_text = response.json().get('response', '').strip()
                        if qa_text:
                            return self.parse_qa_response(qa_text)
                    
                    time.sleep(retry_delay)
                    
                except requests.exceptions.Timeout:
                    print(f"Timeout on attempt {attempt + 1} for {keyword}")
                    time.sleep(retry_delay)
                except Exception as e:
                    print(f"Error on attempt {attempt + 1} for {keyword}: {e}")
                    time.sleep(retry_delay)
            
            return []
            
        except Exception as e:
            print(f"Error generating Q&A for {keyword}: {e}")
            return []

    def process_json_file(self, json_path: str):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return

        combined_qa_text = []
        combined_qa_json = {}
        
        for filename, keywords in tqdm(data.items(), desc="Processing files"):
            file_qa_entries = []
            file_qa_json = {filename: {}} 

            file_output_path_txt = self.output_dir / f"{filename.replace('.pdf', '_qa.txt')}"
            file_output_path_json = self.output_dir / f"{filename.replace('.pdf', '_qa.json')}"

            has_content = False
            
            for keyword, occurrences in keywords.items():
                checkpoint_key = f"{filename}|{keyword}"
                
                if checkpoint_key in self.processed_sections:
                    continue
                
                if occurrences:
                    qa_pairs = self.generate_qa_pairs(filename, keyword, occurrences)
                    if qa_pairs:
                        has_content = True
                        
                        for qa in qa_pairs:
                            qa_text = f"Q: {qa['question']}\nA: {qa['answer']}"
                            file_qa_entries.append(qa_text)
                        
                        file_qa_json[filename][keyword] = []
                        for occurrence in occurrences:
                            new_occurrence = deepcopy(occurrence)
                            new_occurrence['qa_pairs'] = qa_pairs
                            file_qa_json[filename][keyword].append(new_occurrence)
                        
                        self.save_checkpoint(filename, keyword)
            
            if has_content:
                try:
                    with open(file_output_path_txt, 'w', encoding='utf-8') as f:
                        f.write("\n<EOS>\n".join(file_qa_entries))

                    if file_qa_json[filename]:
                        with open(file_output_path_json, 'w', encoding='utf-8') as f:
                            json.dump(file_qa_json, f, indent=2, ensure_ascii=False)
                    
                    combined_qa_text.extend(file_qa_entries)
                    combined_qa_json.update(file_qa_json)
                except Exception as e:
                    print(f"Error writing output files for {filename}: {e}")
        
        try:
            combined_output_path_txt = self.output_dir / "combined_qa.txt"
            combined_output_path_json = self.output_dir / "combined_qa.json"
            
            with open(combined_output_path_txt, 'w', encoding='utf-8') as f:
                f.write("\n<EOS>\n".join(combined_qa_text))
                
            with open(combined_output_path_json, 'w', encoding='utf-8') as f:
                json.dump(combined_qa_json, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing combined output files: {e}")

def main():
    processor = PDFProcessor()
    processor.process_json_file("output_v3.json")

if __name__ == "__main__":
    main()