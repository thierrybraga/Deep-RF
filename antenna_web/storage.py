import json
import os
import uuid
from typing import List, Dict, Optional
from dataclasses import asdict

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'antennas.json')

class AntennaStorage:
    def __init__(self):
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(DATA_FILE):
            # Seed with some examples
            initial_data = [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Dipolo Wi-Fi Padrão",
                    "brand": "Genérico",
                    "technology": "Wi-Fi 2.4GHz",
                    "config": {
                        "type": "dipole",
                        "frequency": 2.45e9,
                        "length": 0.062,
                        "radius": 0.001
                    }
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Patch 5G n78",
                    "brand": "Genérico",
                    "technology": "5G",
                    "config": {
                        "type": "patch",
                        "frequency": 3.5e9,
                        "substrate_er": 2.2,
                        "substrate_h": 0.001575
                    }
                }
            ]
            self._save_data(initial_data)

    def _load_data(self) -> List[Dict]:
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_data(self, data: List[Dict]):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_all(self) -> List[Dict]:
        return self._load_data()

    def get(self, antenna_id: str) -> Optional[Dict]:
        data = self._load_data()
        for antenna in data:
            if antenna['id'] == antenna_id:
                return antenna
        return None

    def create(self, antenna_data: Dict) -> Dict:
        data = self._load_data()
        if 'id' not in antenna_data or not antenna_data['id']:
            antenna_data['id'] = str(uuid.uuid4())
        
        # Ensure config exists
        if 'config' not in antenna_data:
            antenna_data['config'] = {}
            
        data.append(antenna_data)
        self._save_data(data)
        return antenna_data

    def update(self, antenna_id: str, antenna_data: Dict) -> Optional[Dict]:
        data = self._load_data()
        for i, antenna in enumerate(data):
            if antenna['id'] == antenna_id:
                # Update fields, keeping ID
                antenna_data['id'] = antenna_id
                data[i] = antenna_data
                self._save_data(data)
                return antenna_data
        return None

    def delete(self, antenna_id: str) -> bool:
        data = self._load_data()
        initial_len = len(data)
        data = [a for a in data if a['id'] != antenna_id]
        if len(data) < initial_len:
            self._save_data(data)
            return True
        return False

storage = AntennaStorage()
