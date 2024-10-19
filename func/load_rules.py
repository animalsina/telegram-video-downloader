import re
import glob
import os

rules = {'message': []}

def load_rules(root_directory):
    """
    Carica tutte le regole dai file .rule nella directory specificata.
    """

    rule_files = os.path.join(root_directory, 'rules', '*.rule')  # Cambiato per cercare direttamente nella directory
    for rule_file in glob.glob(rule_files):
        with open(rule_file, 'r') as f:
            pattern = None  # Variabile per memorizzare temporaneamente il pattern
            for line in f:
                if line.startswith("on:message:pattern"):
                    match = re.search(r'="(.*?)"', line)
                    if match:  # Controlla se il pattern è stato trovato
                        pattern = match.group(1)  # Assegna il pattern
                elif pattern and line.startswith("action:message:translate"):
                    match = re.search(r'="(.*?)"', line)
                    if match:  # Controlla se l'azione è stata trovata
                        action = match.group(1)  # Assegna l'azione
                        # Aggiungi un dizionario con il pattern e l'azione alla lista delle regole
                        rules['message'].append({'pattern': pattern, 'action': action})
                        pattern = None  # Resetta il pattern dopo aver creato la regola
    return rules

def apply_rules(type_name, input_value):
    """
    Applica le regole al testo fornito e restituisce il risultato trasformato.
    """

    # Rules for messages
    if type_name == 'message':
        for rule in rules['message']:
            pattern = rule['pattern']
            action = rule['action']
            match = re.match(pattern, input_value)
            if match:
                return action.format(*match.groups())
    return input_value
