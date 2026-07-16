import json
import os

log_path = r'C:\Users\110778\.gemini\antigravity\brain\40543bbf-61ce-4ffe-b9c5-a6bca24669c3\.system_generated\logs\transcript.jsonl'
py_file = r'C:\Users\110778\OneDrive - Secure Meters Ltd\Desktop\Multi-Language_Display_Translator_Tool\Source_Code\Multi_Language_Translator.py'
spec_file = r'C:\Users\110778\OneDrive - Secure Meters Ltd\Desktop\Multi-Language_Display_Translator_Tool\Source_Code\Multi_Language_Translator.spec'

changes = []

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            entry = json.loads(line)
        except:
            continue
        if 'tool_calls' in entry:
            for call in entry['tool_calls']:
                tool_name = call.get('tool_name', '')
                args = call.get('tool_args', {})
                if tool_name in ['replace_file_content', 'multi_replace_file_content']:
                    target = args.get('TargetFile', '')
                    if target in [py_file, spec_file]:
                        changes.append((tool_name, args))

# Now we apply the inverse of the changes from newest to oldest
for file_path in [py_file, spec_file]:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # reverse the changes for this file
    file_changes = [c for c in changes if c[1].get('TargetFile') == file_path]
    file_changes.reverse()
    
    for tool_name, args in file_changes:
        if tool_name == 'replace_file_content':
            target = args['TargetContent']
            replacement = args['ReplacementContent']
            # inverse: replace 'replacement' with 'target'
            if replacement in content:
                content = content.replace(replacement, target)
            else:
                print(f"Warning: could not find replacement content to undo in {file_path}")
        elif tool_name == 'multi_replace_file_content':
            chunks = args.get('ReplacementChunks', [])
            # apply chunks in any order since they shouldn't overlap if we're just doing exact string replacement
            for chunk in chunks:
                target = chunk['TargetContent']
                replacement = chunk['ReplacementContent']
                if replacement in content:
                    content = content.replace(replacement, target)
                else:
                    print(f"Warning: could not find chunk replacement content to undo in {file_path}")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

print('Undo complete')
