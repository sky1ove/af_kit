# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_prepare_json.ipynb.

# %% auto 0
__all__ = ['get_AF_input_seq', 'write_json', 'read_json', 'a3m_to_seq', 'get_protein_json', 'get_AF_input', 'save_json',
           'generate_pair_df', 'save_input', 'get_AF_input_smi', 'save_input_smi']

# %% ../nbs/00_prepare_json.ipynb 3
import os, json, pandas as pd
from pathlib import Path
from tqdm import tqdm
from itertools import combinations

# %% ../nbs/00_prepare_json.ipynb 10
def get_AF_input_seq(name, seq):
    "Generate AF input file of protein sequence only"
    
    json_data = {
        "name": name,
        "modelSeeds": [1],
        "sequences": [
            {
                "protein": {
                    "id": "A",
                    "sequence": seq,
                }
            },
        ],
        "bondedAtomPairs": [],
        "dialect": "alphafold3",
        "version": 2
    }
    return json_data

# %% ../nbs/00_prepare_json.ipynb 12
def write_json(data, save_path):
    with open(save_path,'w') as f: 
        json.dump(data,f,indent=4)

# %% ../nbs/00_prepare_json.ipynb 14
def read_json(file_path):
    with open(file_path,'r') as f: 
        data = json.load(f)
    return data

# %% ../nbs/00_prepare_json.ipynb 17
def a3m_to_seq(file_path:Path):
    "Get protein sequence from a3m file"
    return file_path.read_text().splitlines()[2] # protein sequence is located on line 2

# %% ../nbs/00_prepare_json.ipynb 19
def get_protein_json(gene_name, a3m_dir=".",idx = 'A',run_template=True):
    "Get alphafold format protein json from a3m file; make sure a3m_dir is under af_input"
    file_path = Path(a3m_dir)/f"{gene_name}.a3m"
    protein_sequence = a3m_to_seq(file_path)
    
    json_data = {
        'id': idx,
        'sequence': protein_sequence, 
        'modifications': [],
        'unpairedMsaPath': "/root/af_input/"+str(file_path), # for docker path, ECD under af_input
        'pairedMsa': '',
        'templates': None if run_template else []
    }

    return json_data

# %% ../nbs/00_prepare_json.ipynb 22
def get_AF_input(gene_list,a3m_dir,run_template=True):
    'Get AF3 input json data, allows multiple genes/proteins'
    sequences = []
    alphabets = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    for index, gene in enumerate(gene_list):
        protein_json=get_protein_json(gene,a3m_dir,idx=alphabets[index],run_template=run_template)
        sequences.append({'protein':protein_json})
    name = '_'.join(gene_list)
    json_data = {
            "name": name,
            "modelSeeds": [1],
            "sequences": sequences,
            "bondedAtomPairs": [],
            "dialect": "alphafold3",
            "version": 2
        }
    return json_data

# %% ../nbs/00_prepare_json.ipynb 25
def save_json(json_data, folder):
    "Save json to file"
    file_path = Path(folder)/f"{json_data['name']}.json"
    with open(file_path,'w') as f: json.dump(json_data,f,indent=4)

# %% ../nbs/00_prepare_json.ipynb 27
def generate_pair_df(gene_list,self_pair=True):
    "Unique pair genes in a gene list"
    pairs = list(combinations(gene_list, 2))
    pair_df = pd.DataFrame(pairs,columns=["Gene1", "Gene2"])
    
    if self_pair:
        self_pair_df = pd.DataFrame({'Gene1':gene_list, 'Gene2':gene_list})
        pair_df = pd.concat([pair_df,self_pair_df])

    return pair_df.reset_index(drop=True)

# %% ../nbs/00_prepare_json.ipynb 30
def save_input(pair_df, a3m_dir, save_dir, nfolder=4):
    "Save Alphafold input file in a directory with separate folder for parallel calculating"
    
    save_dir = Path(save_dir) 
    
    for idx, row in tqdm(pair_df.iterrows(),total=len(pair_df)):
        for n in range(nfolder):
            folder_path = save_dir / f'folder_{n}'
            folder_path.mkdir(parents=True, exist_ok=True)

        # for faster speed, can removethe check
        # check_fname = list(save_dir.glob(f'*/{row["Gene1"]}_{row["Gene2"]}.json'))
        # if not check_fname: 
            
        json_data = get_AF_input([row['Gene1'], row['Gene2']], a3m_dir=a3m_dir)  
        save_fname = save_dir / f'folder_{idx % nfolder}' / f'{row["Gene1"]}_{row["Gene2"]}.json'
        write_json(json_data,save_fname)        

# %% ../nbs/00_prepare_json.ipynb 37
def get_AF_input_smi(smi_idx, smiles, protein_json):
    "Generate AF input file for smiles protein docking task"
    
    json_data = {
        "name": smi_idx,
        "modelSeeds": [1],
        "sequences": [
            {
                "ligand": {
                    "id": "L",
                    "smiles": smiles,
                }
            }, 
            {
                "protein": protein_json["sequences"][0]["protein"]
            },
        ],
        "bondedAtomPairs": [],
        "dialect": "alphafold3",
        "version": 2
    }
    return json_data

# %% ../nbs/00_prepare_json.ipynb 40
def save_input_smi(df, id_col, smi_col, protein_json,save_dir):
    
    for i, r in tqdm(df.iterrows(),total=len(df)):
        
        json_data = get_AF_input_smi(r[id_col], r[smi_col],protein_json)
        file_name =Path(save_dir)/f"{r[id_col]}.json"
        write_json(json_data,file_name)
