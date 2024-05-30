from flask import Flask, jsonify,request
import chromadb
from chromadb.config import Settings
from flask_cors import CORS
import requests

app = Flask(__name__)

CORS(app)


# Définir l'endpoint API et les headers
api_endpoint = "http://localhost:5001/api/v1/generate"
headers = {
    "Content-Type": "application/json"
}

def create_first_prompt(query, context):
      return (f"Vous êtes un generateur des histoire de jeux, voici un exemple d'histoire: {context}\n\n  Ci-dessous se trouve une instruction qui décrit une tâche, associée à une entrée fournissant plus de contexte. Écrivez une réponse qui complète correctement la demande  en français, Generer une histoire de jeu qui inclut des mini-challenges basé sur mecanique didactique et mini-scenario suivant: ### Instruction : {query}.\n\n### Response:\n.")


def get_context(query):

    # Initialiser le client Chroma
    persistent_client = chromadb.PersistentClient(path="./chroma_db_vectors")

    collection = persistent_client.get_collection(name="games_stories")

    results = collection.query(
        query_texts=[query], # Chroma will embed this for you
        n_results=2
    )
    context = results['metadatas'][0][0]['story']
    print(context)
    return context
     
@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    query = data.get('query', '')
    
    content = ""
    continue_generating = True

    full_query = create_first_prompt(query, get_context(query))
    
    payload = {
            "n": 1,
            "max_context_length": 2048,
            "max_length": 100,
            "temperature": 0.7,
            "top_p": 0.92,
            "top_k": 100,
            "prompt": full_query,
            "quiet": True,
            "stop_sequence": ["### Instruction :", "### Réponse :"],
             "continuation": False
        }

    # Envoyer la requête HTTP POST
    response = requests.post(api_endpoint, json=payload)
    response_data = response.json()

    if response.status_code == 200:
            generated_text = response_data["results"][0]['text']
            content += generated_text
    
    while continue_generating:
            
        full_query = f"\n\n Ci-dessous se trouve une instruction qui décrit une tâche, associée à une entrée fournissant plus de contexte. Écrivez une réponse qui complète correctement la demande  en français, Generer une histoire de jeu qui inclut des mini-challenges basé sur mecanique didactique et mini-scenario suivant: ### Instruction : {query}.\n\n### Response:\n\n {content}"
        payload = {
            "n": 1,
            "max_context_length": 2048,
            "max_length": 100,
            "temperature": 0.7,
            "top_p": 0.92,
            "top_k": 100,
            "prompt": full_query,
            "quiet": True,
            "stop_sequence": ["### Instruction :", "### Réponse :"],
            "continuation": True
        }

        # Envoyer la requête HTTP POST
        response = requests.post(api_endpoint, json=payload)
        

        try:
            response_data = response.json()
        except requests.exceptions.JSONDecodeError as e:
            print(f"Erreur lors du décodage de la réponse JSON: {e}")
            print(f"Réponse brute: {response.text}")
            continue

        if response.status_code == 200:
            generated_text = response_data["results"][0]['text']
            content += generated_text
            print(content+"\n\n")
        else:
            raise Exception(f"Error {response.status_code}: {response_data}")

        # Vérifier si la réponse atteint la limite max de tokens
        if response_data["results"][0]['finish_reason'] != "length":
            continue_generating = False  # Arrêter si la réponse n'atteint pas la limite max de tokens  
 

    return jsonify({"generated_text": content})



if __name__ == '__main__':
    app.run(debug=True)