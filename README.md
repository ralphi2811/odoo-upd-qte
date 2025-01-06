# API de Gestion de Stock Odoo

Cette API permet de gérer les transferts de stock dans Odoo en ajustant les quantités entre un emplacement physique et un emplacement virtuel.

## Configuration

### Variables d'environnement

Créez un fichier `.env` à partir du fichier `.env.example` :
```bash
cp .env.example .env
```

Puis configurez les variables suivantes :
```env
ODOO_URL=https://your-odoo-instance.odoo.com
ODOO_DB=your-database-name
ODOO_USERNAME=your-username
ODOO_PASSWORD=your-password
API_KEY=your-secret-api-key  # Clé secrète pour sécuriser l'accès à l'API
```

Il est recommandé de générer une clé API forte et unique. Vous pouvez utiliser une commande comme celle-ci pour générer une clé aléatoire :
```bash
openssl rand -hex 32
```

## Installation

### Option 1 : Installation locale

1. Créez un environnement virtuel Python :
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

3. Lancez l'API :
```bash
python api.py
```

### Option 2 : Installation avec Docker

1. Construisez l'image :
```bash
docker build -t stock-api .
```

2. Lancez le conteneur :
```bash
docker run -d \
  -p 9999:9999 \
  -e ODOO_URL=your-odoo-url \
  -e ODOO_DB=your-database \
  -e ODOO_USERNAME=your-username \
  -e ODOO_PASSWORD=your-password \
  -e API_KEY=your-secret-api-key \
  stock-api
```

## Utilisation de l'API

### Authentification

Toutes les requêtes à l'API doivent inclure la clé API dans l'en-tête HTTP `X-API-Key`. Sans cette clé ou avec une clé invalide, l'accès sera refusé avec une erreur 403.

### Endpoint

`POST /stock/{default_code}`

### Paramètres de la requête

1. Dans l'URL :
- `default_code` : Code article du produit dans Odoo

2. Dans les en-têtes HTTP :
- `X-API-Key` : Votre clé API secrète
- `Content-Type: application/json`

3. Dans le corps de la requête (JSON) :
```json
{
    "target_quantity": 10.0,
    "company_id": 19,
    "location_id": 192,
    "picking_type_id": 113,
    "destination_location_id": 188
}
```

Description des paramètres :
- `target_quantity` : Quantité cible souhaitée
- `company_id` : ID de la société
- `location_id` : ID de l'emplacement physique
- `picking_type_id` : ID du type de transfert
- `destination_location_id` : ID de l'emplacement virtuel

### Exemple de requête avec curl

```bash
curl -X POST "http://localhost:9999/stock/VOTRE_CODE_ARTICLE" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-secret-api-key" \
     -d '{
           "target_quantity": 10.0,
           "company_id": 19,
           "location_id": 192,
           "picking_type_id": 113,
           "destination_location_id": 188
         }'
```

### Format de la réponse

```json
{
    "product_id": 123,
    "default_code": "VOTRE_CODE_ARTICLE",
    "previous_stock": 5.0,
    "new_stock": 10.0,
    "transfer_done": true,
    "picking_id": 456,
    "message": "Transfert effectué avec succès: ajout de 5.0 unités"
}
```

## Documentation interactive

Une documentation Swagger interactive est disponible à l'adresse :
```
http://localhost:9999/docs
```

## Logique de fonctionnement

1. L'API reçoit une requête avec un code article et une quantité cible
2. Elle vérifie le stock actuel dans l'emplacement physique spécifié
3. Compare avec la quantité cible demandée
4. Effectue un transfert automatique :
   - Si quantité cible > stock actuel : transfert de l'emplacement virtuel vers physique
   - Si quantité cible < stock actuel : transfert de l'emplacement physique vers virtuel

## Sécurité

- L'API est protégée par une authentification via clé API
- La clé doit être fournie dans l'en-tête HTTP `X-API-Key`
- Les requêtes sans clé ou avec une clé invalide seront rejetées (erreur 403)
- Il est recommandé de générer une clé forte et unique
- La clé API doit être gardée secrète et transmise de manière sécurisée

## Notes importantes

- Assurez-vous que les IDs (company_id, location_id, etc.) correspondent à votre configuration Odoo
- L'API nécessite les droits appropriés dans Odoo pour effectuer les transferts
- Le port par défaut est 9999, modifiable dans le code si nécessaire
- Tous les transferts sont tracés dans Odoo avec l'origine "API Transfer - {code_article}"
