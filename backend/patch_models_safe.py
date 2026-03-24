import os
import glob

models_dir = r'c:\Users\guntu\OneDrive\Desktop\model\backend\app\models'
for filepath in glob.glob(os.path.join(models_dir, '*.py')):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replacements for postgresql specific imports
    content = content.replace('from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID', 'from sqlalchemy import JSON as JSONB, String\nfrom sqlalchemy import JSON as ARRAY')
    content = content.replace('from sqlalchemy.dialects.postgresql import JSONB, UUID', 'from sqlalchemy import JSON as JSONB, String')
    content = content.replace('from sqlalchemy.dialects.postgresql import UUID', 'from sqlalchemy import String')
    
    # Check if we need to add uuid import
    if 'UUID(as_uuid=True)' in content and 'import uuid' not in content:
        lines = content.split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('from __future__'):
                insert_idx = i + 1
        lines.insert(insert_idx, 'import uuid')
        content = '\n'.join(lines)
        
    # Replace UUID column definitions
    content = content.replace('UUID(as_uuid=True)', 'String(36)')
    content = content.replace('server_default=text("gen_random_uuid()")', 'default=lambda: __import__("uuid").uuid4().hex')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Models patched safely with proper import order!")
