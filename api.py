from fastapi import FastAPI, HTTPException
import xmlrpc.client
from typing import Optional
from pydantic import BaseModel

app = FastAPI()

import os
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration Odoo
url = os.getenv('ODOO_URL')
db = os.getenv('ODOO_DB')
username = os.getenv('ODOO_USERNAME')
password = os.getenv('ODOO_PASSWORD')

if not all([url, db, username, password]):
    raise ValueError("Toutes les variables d'environnement Odoo doivent être définies")

# Connexion Odoo
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

class StockUpdate(BaseModel):
    target_quantity: float
    company_id: int
    location_id: int  # Emplacement physique
    picking_type_id: int
    destination_location_id: int  # Emplacement virtuel

class StockResponse(BaseModel):
    product_id: int
    default_code: str
    previous_stock: float
    new_stock: float
    transfer_done: bool
    picking_id: Optional[int] = None
    message: str

@app.post("/stock/{default_code}", response_model=StockResponse)
async def update_stock(default_code: str, stock_update: StockUpdate):
    try:
        # 1. Recherche du produit par default_code
        product_variants = models.execute_kw(db, uid, password, 'product.product', 'search_read', 
            [[['default_code', '=', default_code]]], 
            {'fields': ['id', 'name', 'default_code'], 'limit': 1}
        )
        
        if not product_variants:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        
        product_id = product_variants[0]['id']
        
        # 2. Récupération du stock actuel dans location physique
        stock = models.execute_kw(db, uid, password, 'stock.quant', 'search_read', 
            [[['product_id', '=', product_id], ['location_id', '=', stock_update.location_id]]], 
            {'fields': ['quantity']}
        )
        
        current_stock = stock[0]['quantity'] if stock else 0.0
        target_quantity = stock_update.target_quantity
        
        # Calcul de la différence pour déterminer le transfert nécessaire
        difference = target_quantity - current_stock
        
        # Si pas de différence, pas besoin de transfert
        if difference == 0:
            return StockResponse(
                product_id=product_id,
                default_code=product_variants[0]['default_code'],
                previous_stock=current_stock,
                new_stock=current_stock,
                transfer_done=False,
                message="Pas de transfert nécessaire, stock déjà à la quantité cible"
            )
            
        # 3. Création du transfert
        # Si difference > 0: on ajoute du stock (transfert du virtuel vers physique)
        # Si difference < 0: on retire du stock (transfert du physique vers virtuel)
        if difference > 0:
            source_location_id = stock_update.destination_location_id  # virtuel
            destination_location_id = stock_update.location_id  # physique
            quantity = abs(difference)
        else:
            source_location_id = stock_update.location_id  # physique
            destination_location_id = stock_update.destination_location_id  # virtuel
            quantity = abs(difference)
            
        # Création du picking
        picking_id = models.execute_kw(db, uid, password, 'stock.picking', 'create', [{
            'picking_type_id': stock_update.picking_type_id,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'origin': f'API Transfer - {default_code}',
            'company_id': stock_update.company_id
        }])

        # Création du mouvement
        move_vals = {
            'name': f'Transfer API {default_code}',
            'picking_id': picking_id,
            'product_id': product_id,
            'product_uom_qty': quantity,
            'product_uom': 1,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'company_id': stock_update.company_id
        }

        models.execute_kw(db, uid, password, 'stock.move', 'create', [move_vals])

        # Validation du transfert
        models.execute_kw(db, uid, password, 'stock.picking', 'action_confirm', [[picking_id]])
        models.execute_kw(db, uid, password, 'stock.picking', 'action_assign', [[picking_id]])
        models.execute_kw(db, uid, password, 'stock.picking', 'button_validate', [[picking_id]])

        return StockResponse(
            product_id=product_id,
            default_code=product_variants[0]['default_code'],
            previous_stock=current_stock,
            new_stock=target_quantity,
            transfer_done=True,
            picking_id=picking_id,
            message=f"Transfert effectué avec succès: {'ajout' if difference > 0 else 'retrait'} de {abs(difference)} unités"
        )

    except xmlrpc.client.Fault as e:
        raise HTTPException(status_code=400, detail=f"Erreur Odoo: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9999)
