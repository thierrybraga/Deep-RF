import os

root_dir = "d:/Github/iLoveAntennas/src/iloveantennas"

for dirpath, _, filenames in os.walk(root_dir):
    for f in filenames:
        if f.endswith('.py'):
            filepath = os.path.join(dirpath, f)
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
            
            new_content = content.replace("from core.", "from iloveantennas.simulator.core.")
            new_content = new_content.replace("import core.", "import iloveantennas.simulator.core.")
            new_content = new_content.replace("from solver.", "from iloveantennas.simulator.solver.")
            new_content = new_content.replace("from visualization.", "from iloveantennas.simulator.visualization.")
            new_content = new_content.replace("from fem.", "from iloveantennas.simulator.fem.")
            new_content = new_content.replace("from utils.", "from iloveantennas.simulator.utils.")
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                print(f"Fixed {filepath}")
