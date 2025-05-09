# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/03_analyze.ipynb.

# %% auto 0
__all__ = ['read_summary_json', 'get_summary_df', 'process_summary_df', 'get_top_cases', 'get_3d_report', 'get_report',
           'copy_file']

# %% ../nbs/03_analyze.ipynb 3
import json, shutil, pandas as pd
from pathlib import Path
import plotly.graph_objects as go

# %% ../nbs/03_analyze.ipynb 5
def read_summary_json(json_path):
    "Read json file to dictionary"
    json_path = Path(json_path)
    json_data=json.loads(json_path.read_text())
        
    # Flatten the JSON data into a single row
    row = {"ID": json_path.stem}
    for key, value in json_data.items():
        if isinstance(value, list):
            for idx, sub_value in enumerate(value):
                if isinstance(sub_value, list):
                    for sub_idx, sub_sub_value in enumerate(sub_value):
                        row[f"{key}_{idx}_{sub_idx}"] = sub_sub_value
                else:
                    row[f"{key}_{idx}"] = sub_value
        else:
            row[key] = value
    return row

# %% ../nbs/03_analyze.ipynb 7
def get_summary_df(output_dir):
    "Pack the summary json from the output folder to the df"
    
    path_list = list(Path(output_dir).rglob('*_summary_confidences.json'))
    print(len(path_list),'summary_confidences.json files detected')
    return pd.DataFrame(list(map(read_summary_json,path_list)))

# %% ../nbs/03_analyze.ipynb 10
def process_summary_df(df,generate_report=False):
    "Post process the json-converted pandas df; remove redundant columns; available for pairs"
    
    df['ID'] = df.ID.str.replace('_summary_confidences','')
    df = df.set_index('ID')

    # drop zero std columns: usually contains chain_pair_pae_min_0_0 and has_clash
    zero_std_cols = df.columns[df.std()<1e-10]
    df=df.drop(columns=zero_std_cols)

    # drop columns with same values
    redundant_columns = []
    
    # Check for columns equal to `iptm`
    for col in ['chain_iptm_0', 'chain_iptm_1', 'chain_pair_iptm_0_1', 'chain_pair_iptm_1_0']:
        if df['iptm'].equals(df[col]):
            redundant_columns.append(col)
    
    # Check for columns equal to `chain_ptm_0`
    if df['chain_ptm_0'].equals(df['chain_pair_iptm_0_0']):
        redundant_columns.append('chain_pair_iptm_0_0')
    
    # Check for columns equal to `chain_ptm_1`
    if df['chain_ptm_1'].equals(df['chain_pair_iptm_1_1']):
        redundant_columns.append('chain_pair_iptm_1_1')
    
    # Drop redundant columns
    df = df.drop(columns=redundant_columns)
    
    if generate_report:
        print('Generating pairplot graph report')
        sns.pairplot(data=df, corner=True)
        plt.savefig("af_report.pdf")
        plt.close()
        print('Export to af_report.pdf')

    # add iptm and ptm
    df['iptm_ptm_add'] = df['iptm']+df['ptm']

    # inter error add
    df['chain_pair_pae_min_add'] = df['chain_pair_pae_min_0_1']+df['chain_pair_pae_min_1_0']

    # rank iptm and ptm and add the rank, this method can ignore the different value range between iptm and ptm
    df['iptm_rnk'],df['ptm_rnk'] = df.iptm.rank(ascending=False), df.ptm.rank(ascending=False)
    df['iptm_ptm_rnk_add'] = df['iptm_rnk']+df['ptm_rnk']

    # combine chain_pair_pae_min & iptm rank
    df['chain_pair_pae_min_add_rnk'] = df['chain_pair_pae_min_add'].rank()
    df['iptm_pae_add_rnk'] = df['chain_pair_pae_min_add_rnk'] + df['iptm_rnk']
    
    return df

# %% ../nbs/03_analyze.ipynb 12
def get_top_cases(df,n=30):
    "Get top cases from the metric"
    idxs = set()
    
    big_cols = ['ranking_score', 'iptm', 'iptm_ptm_add']
    small_cols = [
        'iptm_ptm_rnk_add', 
        'chain_pair_pae_min_add', 
        'chain_pair_pae_min_0_1', 
        'chain_pair_pae_min_1_0', 
        'iptm_pae_add_rnk'
    ]
    
    for col in big_cols: idxs.update(df.nlargest(n, col).index)
    for col in small_cols: idxs.update(df.nsmallest(n, col).index)

    return list(idxs)

# %% ../nbs/03_analyze.ipynb 14
def get_3d_report(df,index_list, x='iptm',y='ptm',z='chain_pair_pae_min_add',save_dir='af_report'):
    "Generate 3d plot html file given case index and x, y, z colname"
    annotation = df.index.where(df.index.isin(index_list),'').str.split('_').str[1]

    # Create the 3D scatter plot
    fig = go.Figure(data=go.Scatter3d(
        x=df[x],
        y=df[y],
        z=df[z],
        mode='markers+text',
        text=annotation,  # Annotation using the index
        textposition="top center",
        marker=dict(size=8, color='blue', opacity=0.8),
    ))
    
    # Customize layout
    fig.update_layout(
        scene=dict(
            xaxis_title=x,
            yaxis_title=y,
            zaxis_title=z,
        ),
        title='3D Scatter Plot',
        autosize=True,
        height=3000,
    )
    
    fig.write_html(Path(save_dir)/'3d_scatter_plot.html',full_html=True)
    print('Exported the html to 3d_scatter_plot.html')

# %% ../nbs/03_analyze.ipynb 16
def get_report(out_dir,save_dir='af_report'):
    "Generate summary report based on summary_confidences file; return summary df and top cases"
    out = get_summary_df(out_dir)
    out = process_summary_df(out)
    top_cases = get_top_cases(out)
    
    Path(save_dir).mkdir(exist_ok=True)
    get_3d_report(out,top_cases,save_dir=save_dir)
    out.to_csv(Path(save_dir)/'summary_confidences.csv')
    
    return out, top_cases

# %% ../nbs/03_analyze.ipynb 18
def copy_file(idx_name, source_dir, dest_dir):
    "Copy all model cif generated by AF3 to the new dest folder"
    source_path = Path(source_dir)/f"{idx_name}/{idx_name}_model.cif"
    dest_path = Path(dest_dir)/f"{idx_name}_model.cif"
    shutil.copy(source_path,dest_path)
    print(f'Copying {str(source_path)} to {str(dest_path)}')
