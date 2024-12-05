## Training data for MGIS INsurance pdf data

## Steps
1. Create a virtual env and install ```pip install PyMUPDF```
2. Run the ```python3 pdf-extract-2.py``` to output a json file with rows, pagenumber and sections from the pdf
3. Current geenrated json for all 22 PDF files is ```pdf_structure_<datetime>.json``` (hardcoded in the main Ollama run python file ```ollama_section_to_paras.py```)
4. Run the ```python3 ollama_Section_to_paras.py``` to generate all the "sectional stories" along with <EOS> token at the end

   
## Base prompt 
```
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

```

NOTE : The Ollama- Mistral needs to be setup on the laptop locally for running this script
