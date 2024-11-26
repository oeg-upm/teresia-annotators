from pathlib import Path
import json
import re
from typing import List, Tuple

def generate_inflections(word: str) -> List[str]:
    """
    Generate possible inflected forms of a word, considering Spanish grammar.
    Handles singular and plural forms.
    """
    inflections = [word]
    if word.endswith(('a', 'e', 'i', 'o', 'u')):
        inflections.append(word + 's')
    elif word.endswith(('á', 'é', 'í', 'ó', 'ú')):
        inflections.append(word[:-1] + 'es')
    elif word.endswith('z'):
        inflections.append(word[:-1] + 'ces')
    else:
        inflections.append(word + 'es')
    return inflections

def build_inflected_patterns(expression: str) -> List[str]:
    """
    Build regex patterns for the given expression, including inflected forms for each word.
    """
    words = expression.split()
    if len(words) == 1:
        # Single word case
        return [re.escape(inflected) for inflected in generate_inflections(expression)]
    else:
        # Multiword expression case
        inflected_forms = [generate_inflections(word) for word in words]
        # Build regex patterns for all combinations of inflected forms
        patterns = []
        for combo in zip(*inflected_forms):
            patterns.append(r' '.join(map(re.escape, combo)))
        return patterns

def find_offsets_and_forms(text: str, expression: str) -> List[Tuple[Tuple[int, int], str]]:
    """
    Find occurrences of the word or multiword expression in the text.
    Ignores punctuation and considers plural inflections.
    Returns the offsets and the exact matched form.
    """
    # Generate patterns considering inflections
    patterns = build_inflected_patterns(expression)
    # Allow patterns to ignore punctuation around words
    punctuation_aware_pattern = r'\b(?:{})\b'.format('|'.join(patterns))
    
    matches = []
    for match in re.finditer(punctuation_aware_pattern, text, re.IGNORECASE):
        matched_text = match.group()  # Includes the exact matched form
        # Extract offsets for the exact form
        start, end = match.span()
        matches.append(((start, end), matched_text))
    return matches

def filter_offsets_across_words(data):
    """
    Filters offsets across words, ensuring no offset for a word is included in the offsets of another word.

    Args:
        data (dict): Dictionary with words as keys and a list of (start, end) tuples as values.

    Returns:
        dict: A dictionary with filtered offsets where no offset is included in the offsets of another word.
    """
    filtered_data = {}
    
    for current_word, current_offsets in data.items():
        filtered_offsets = []
        
        for current_offset in current_offsets:
            start1, end1 = current_offset
            is_contained = False
            
            for other_word, other_offsets in data.items():
                if current_word == other_word:
                    continue  # Skip checking against the same word
                
                for start2, end2 in other_offsets:
                    # Check if the current offset is fully contained within another offset
                    if start1 >= start2 and end1 <= end2:
                        is_contained = True
                        # Only keep the longer one (current vs other)
                        if end2 - start2 > end1 - start1:
                            break
            
            # Add the offset only if it is not contained within any other
            if not is_contained:
                filtered_offsets.append(current_offset)
        
        # Store the filtered offsets for the current word
        filtered_data[current_word] = filtered_offsets

    return filtered_data

# termtypes dpje: Gral. (general), Lab. (laboral)

def search_in_dle(dje_data, text, results, termtype='Lab.'):
    for concept_record in dje_data:
        domains = []
        for domain_info in concept_record["Body"]:
            domains.append(domain_info['Type'])
        if termtype in domains:
            subterm_positions = []
            if 'SubLemas' in concept_record.keys():
                for subterm_info in concept_record['SubLemas']:
                    subterm = subterm_info['Text']
                    subterm_results = find_offsets_and_forms(text, subterm)
                    if len(subterm_results) > 0:
                        for subterm_result in subterm_results:
                            subterm_positions, subterm_form = subterm_result
                            if subterm_form not in results.keys():
                                results[subterm_form] = [subterm_positions]
                            else:
                                results[subterm_form].append(subterm_positions)            
            term_results = find_offsets_and_forms(text, concept_record['Name'])
            if len(term_results) > 0 :
                for term_result in term_results:
                    term_positions, term_form = term_result
                    if term_form not in results.keys():
                        results[term_form] = [term_positions]
                    else:
                        results[term_form].append(term_positions)  
    results = filter_offsets_across_words(results)

    return results



def execute_annotator(pathDPEJ,path_articulos,path_salida):

    #pathDPEJ = r'C:\Users\pdiez\Documents\TeresIA\Anotacion_estatuto_dje'
    #articles_folder = 'articulos_estatuto'
    #out_folder = r'anotaciones_estatuto\anotaciones_estatuto_completo'
    
    dje_file = open(Path(pathDPEJ, 'LemasInfo-dje.json'), encoding='utf8')
    dje_data = json.load(dje_file)
    
    # iteramos sobre todos los artículos del estatuto y los abrimos
    for path in Path(path_articulos).iterdir():
        if path.is_file() and path.suffix == '.txt':
            path_in_str = str(path)  
            f = open(path_in_str, encoding='utf8')
            data = f.read()  
            print(path)
    
            resultados = {}
            resultados = search_in_dle(dje_data, data, resultados)
    
            # save results
            file_name = f"{Path(path_in_str).stem}.ann"
            out_file = Path(path_salida, file_name)
            f = open(out_file, 'w', encoding="utf8")
            ind = 1
            for term in resultados.keys():
                for start, end in resultados[term]:
                    term_id = f"T{ind}"                    
                    ind += 1
                    term_type = 'concept'
                    formated_data = f"{term_id}\t{term_type} {start} {end}\t{term.strip()}\n"
                    f.write(formated_data)
            f.close()
        
        
        
import argparse
import os

def main():
    # Crear un parser para los argumentos
    parser = argparse.ArgumentParser(description="Procesar tres rutas de archivo o directorio.")
    
    # Añadir los tres argumentos
    parser.add_argument('pathDPEJ', type=str, help="Ruta del primer archivo o directorio.")
    parser.add_argument('pathIN', type=str, help="Ruta del segundo archivo o directorio.")
    parser.add_argument('pathOUT', type=str, help="Ruta del tercer archivo o directorio.")
    
    # Parsear los argumentos
    args = parser.parse_args()
    
    # Validar si las rutas existen
    for idx, path in enumerate([args.pathDPEJ, args.pathIN, args.pathOUT], start=1):
        if os.path.exists(path):
            print(f"La ruta {idx}: '{path}' existe.")
        else:
            print(f"Advertencia: La ruta {idx}: '{path}' no existe.")
            
    
    execute_annotator(args.pathDPEJ, args.pathIN, args.pathOUT)
            
    
if __name__ == "__main__":
    main()