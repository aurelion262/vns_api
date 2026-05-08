from fastapi import APIRouter
import os

router = APIRouter(prefix="/api/v1/experiment", tags=["Experiment Schema"])

@router.get("/schema")
def get_schemas():
    try:
        # Path to the schema documentation file
        filepath = os.path.join(os.path.dirname(__file__), "..", "docs", "vnstock-data", "unified-ui", "08-schema-reference.md")
        
        if not os.path.exists(filepath):
            return {"data": []}
            
        schemas = []
        current_layer = ''
        current_func_names = []
        current_headers = []
        current_rows = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if line.startswith('## '):
                current_layer = line[3:].strip()
            elif line.startswith('### '):
                if current_func_names and current_rows:
                    for fn in current_func_names:
                        schemas.append({
                            "layer": current_layer,
                            "function": fn,
                            "fields": current_rows
                        })
                    current_rows = []
                # Handle headings with multiple functions: ### `a` / `b`
                raw = line[4:].strip().replace('`', '')
                current_func_names = [f.strip() for f in raw.split('/') if f.strip()]
            elif line.startswith('|'):
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if not cells or '---' in cells[0]:
                    continue
                if not current_headers or cells == ['Column Name (Cột)', 'Dtype', 'Ý Nghĩa (Meaning)', 'Sample Value']:
                    current_headers = ['column', 'dtype', 'meaning', 'sample']
                else:
                    if len(cells) == len(current_headers):
                        row_data = dict(zip(current_headers, cells))
                        for k in row_data:
                            row_data[k] = row_data[k].replace('**', '').replace('`', '')
                        current_rows.append(row_data)
                    
        if current_func_names and current_rows:
            for fn in current_func_names:
                schemas.append({
                    "layer": current_layer,
                    "function": fn,
                    "fields": current_rows
                })
            
        return {"data": schemas}
    except Exception as e:
        return {"data": []}
