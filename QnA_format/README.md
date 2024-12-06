## Running steps 
Same as Earlier 
Just run ```ollama_section_to_paras-QnA.py``` using the ```output_v3.json``` file outputted from running ```pdf-extract-3.py```

### Keywords used to generate answers about -
```
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
```

### Base Prompt
```
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
```
