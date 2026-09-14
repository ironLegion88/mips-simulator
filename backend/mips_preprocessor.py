import re
import logging

logger = logging.getLogger(__name__)

class MipsPreprocessor:
    def __init__(self):
        self.macros = {}
        self.errors = []

    def _add_error(self, message):
        self.errors.append({"message": message})
        logger.error(f"Preprocessor error: {message}")

    def preprocess(self, files: list[dict]) -> list[dict]:
        """
        Takes a list of files [{'filename': '...', 'content': '...'}, ...]
        Returns a list of dictionaries representing the merged assembly with macros expanded:
        [{'filename': 'main.s', 'line_num': 5, 'text': 'add $t0, $t1, $t2'}, ...]
        """
        self.macros = {}
        self.errors = []
        
        merged_lines = []
        for file in files:
            filename = file.get('filename', 'unknown.s')
            content = file.get('content', '')
            for i, line in enumerate(content.splitlines()):
                merged_lines.append({
                    'filename': filename,
                    'line_num': i + 1,
                    'text': line
                })
            
        # First, extract all macro definitions.
        processed_lines = []
        in_macro_def = False
        current_macro_name = ""
        current_macro_args = []
        current_macro_body = []
        
        macro_def_re = re.compile(r'^\s*%macro\s+([a-zA-Z_]\w*)\s*(?:\((.*?)\))?\s*$')
        macro_end_re = re.compile(r'^\s*%end_macro\s*$')
        
        for line_obj in merged_lines:
            line_text = line_obj['text']
            if not in_macro_def:
                match = macro_def_re.match(line_text)
                if match:
                    in_macro_def = True
                    current_macro_name = match.group(1)
                    args_str = match.group(2)
                    if args_str:
                        current_macro_args = [arg.strip() for arg in args_str.split(',')]
                    else:
                        current_macro_args = []
                    current_macro_body = []
                else:
                    processed_lines.append(line_obj)
            else:
                if macro_end_re.match(line_text):
                    in_macro_def = False
                    self.macros[current_macro_name] = {
                        "args": current_macro_args,
                        "body": current_macro_body
                    }
                else:
                    current_macro_body.append(line_text)
                    
        if in_macro_def:
            self._add_error(f"Unclosed macro definition for '{current_macro_name}'")
            
        if self.errors:
            return []

        expanded_lines = self._expand_lines(processed_lines, depth=0)
        return expanded_lines

    def _expand_lines(self, lines: list[dict], depth: int) -> list[dict]:
        if depth > 100:
            self._add_error("Maximum macro recursion depth exceeded.")
            return []
            
        expanded = []
        
        for line_obj in lines:
            line = line_obj['text']
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                expanded.append(line_obj)
                continue
                
            parts = re.split(r'\s+', line_stripped, maxsplit=1)
            first_word = parts[0].split('#')[0].strip()
            
            label_match = re.match(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)', line)
            
            check_word = first_word
            args_str = parts[1] if len(parts) > 1 else ""
            prefix = ""
            
            if label_match:
                prefix = line[:line.find(label_match.group(1)) + len(label_match.group(1)) + 1] # "label:"
                remainder = label_match.group(2).strip()
            else:
                remainder = line_stripped
                
            macro_name = ""
            args_str = ""
            
            call_match = re.match(r'^([%a-zA-Z_]\w*)\s*(?:\((.*?)\)|(.*))?$', remainder)
            if call_match:
                macro_name = call_match.group(1)
                args_str = call_match.group(2) if call_match.group(2) is not None else call_match.group(3)
                if args_str is None:
                    args_str = ""
            
            if macro_name.startswith('%') and macro_name[1:] in self.macros:
                macro_name = macro_name[1:]
            
            if macro_name in self.macros:
                call_args = [arg.strip() for arg in args_str.split(',')] if args_str else []
                macro_def = self.macros[macro_name]
                
                if len(call_args) == 1 and call_args[0] == "":
                    call_args = []
                
                if len(call_args) != len(macro_def["args"]):
                    self._add_error(f"Macro '{macro_name}' expects {len(macro_def['args'])} arguments, got {len(call_args)} at {line_obj['filename']}:{line_obj['line_num']}")
                    expanded.append(line_obj)
                    continue
                    
                arg_map = dict(zip(macro_def["args"], call_args))
                
                substituted_body = []
                for b_line in macro_def["body"]:
                    sub_line = b_line
                    for arg_name, arg_val in arg_map.items():
                        sub_line = re.sub(r'\b' + re.escape(arg_name) + r'\b', arg_val, sub_line)
                    # Use the line_num and filename from the macro CALL site
                    # so that errors in macro expansion point to the invocation.
                    substituted_body.append({
                        'filename': line_obj['filename'],
                        'line_num': line_obj['line_num'],
                        'text': sub_line
                    })
                    
                if prefix:
                    expanded.append({
                        'filename': line_obj['filename'],
                        'line_num': line_obj['line_num'],
                        'text': prefix
                    })
                    
                body_expanded = self._expand_lines(substituted_body, depth + 1)
                expanded.extend(body_expanded)
            else:
                expanded.append(line_obj)
                
        return expanded
