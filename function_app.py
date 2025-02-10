import azure.functions as func
from azure.storage.blob import BlobServiceClient
import os
import logging
import json
import aiohttp
import os



app = func.FunctionApp()

@app.function_name(name="ProcessWebhook")
@app.route(route="webhook", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET", "POST"])
async def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Webhook received a request.")
    
    try:
        # Read request body
        request_body = req.get_body().decode('utf-8')
        logging.info(f"Received data: {request_body}")
        
        # Check if body is empty
        if not request_body:
            logging.warning("Request body is empty.")
            return func.HttpResponse(
                body="Request body cannot be empty.",
                status_code=400
            )
        
        # Parse JSON
        try:
            json_object = json.loads(request_body)
        except Exception as parse_ex:
            logging.error(f"Failed to parse JSON: {str(parse_ex)}")
            return func.HttpResponse(
                body="Invalid JSON format.",
                status_code=400
            )
        
        # Extract href from events array
        try:
            href = json_object['events'][0]['href']
        except (KeyError, IndexError):
            logging.warning("Missing 'events[0].href' in the request body.")
            return func.HttpResponse(
                body="Invalid request body. 'events[0].href' is required.",
                status_code=400
            )
        
        # Validate href and extract userId
        if not href or 'users/' not in href:
            logging.warning("Invalid 'href' format.")
            return func.HttpResponse(
                body="Invalid 'href' format in the request body.",
                status_code=400
            )
        
        user_id = href.split('users/')[1]
        logging.info(f"Extracted userId: {user_id}")
        
        # Get API authorization token from Printix
        async with aiohttp.ClientSession() as client:
            token_data = {
                'grant_type': 'client_credentials',
                'client_secret': os.environ['PrintixClientSecret'],
                'client_id': os.environ['PrintixClientId']
            }
            
            try:
                async with client.post('https://auth.printix.net/oauth/token', 
                                     data=token_data) as token_response:
                    if not token_response.ok:
                        logging.error(f"Failed to retrieve access token. Status: {token_response.status}")
                        return func.HttpResponse(
                            body="Failed to retrieve access token",
                            status_code=500
                        )
                    
                    auth_response = await token_response.text()
                    
            except Exception as ex:
                logging.error(f"Failed to retrieve access token: {str(ex)}")
                return func.HttpResponse(
                    body="Failed to retrieve access token",
                    status_code=500
                )
            
            try:
                auth_json = json.loads(auth_response)
            except Exception as parse_ex:
                logging.error(f"Failed to parse token response: {str(parse_ex)}")
                return func.HttpResponse(
                    body="Failed to parse token response",
                    status_code=500
                )
            
            access_token = auth_json.get('access_token')
            if not access_token:
                logging.error("Access token is missing in the response.")
                return func.HttpResponse(
                    body="Access token is missing in the response",
                    status_code=500
                )
            
            logging.info(f"Obtained access token: {access_token}")
            
            # Get tenantId from environment variables
            tenant_id = os.environ.get('PrintixTenantId')
            if not tenant_id:
                logging.error("Tenant ID is not configured in environment variables.")
                return func.HttpResponse(
                    body="Tenant ID is not configured",
                    status_code=500
                )
            
                        # Make API call to get user details
            try:
                headers = {
                    'Authorization': f'Bearer {access_token}'
                }
                async with client.get(
                    f'https://api.printix.net/cloudprint/tenants/{tenant_id}/users/{user_id}',
                    headers=headers
                ) as user_response:
                    if not user_response.ok:
                        logging.error(f"Failed to retrieve user details. Status: {user_response.status}")
                        return func.HttpResponse(
                            body="Failed to retrieve user details",
                            status_code=500
                        )
                    
                    user_details = await user_response.text()
                    
            except Exception as ex:
                logging.error(f"Failed to retrieve user details: {str(ex)}")
                return func.HttpResponse(
                    body="Failed to retrieve user details",
                    status_code=500
                )
            
            try:
                user_json = json.loads(user_details)
            except Exception as parse_ex:
                logging.error(f"Failed to parse user details: {str(parse_ex)}")
                return func.HttpResponse(
                    body="Failed to parse user details",
                    status_code=500
                )
            
            user_email = user_json.get('user', {}).get('email')
            if not user_email:
                logging.error("User email is missing in the response.")
                return func.HttpResponse(
                    body="User email is missing in the response",
                    status_code=500
                )
             # After getting user_email, lookup in CSV file to get the card number
            connection_string = os.environ['StorageConnectionString']
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            container_client = blob_service_client.get_container_client("cuttysark-accesscards")
            blob_client = container_client.get_blob_client("UserCardDetails.csv")
            
            # Download and process CSV
            download_stream = blob_client.download_blob()
            csv_content = download_stream.readall().decode('utf-8').splitlines()
            
            # Search for user email and get second column
            card_number = None
            for line in csv_content:
                columns = line.split(',')
                if len(columns) >= 2 and columns[0].strip().lower() == user_email.lower():
                    card_number = columns[1].strip()
                    
                    break
            
            if not card_number:
                logging.warning(f"No card number found for email: {user_email}")
                return func.HttpResponse(
                    body="Card number not found for user",
                    status_code=404
                )
            
            logging.info(f"Found card number: {card_number} for email: {user_email}")
            # Convert card_number to base64
            import base64
            card_number_bytes = card_number.encode('utf-8')
            card_number_base64 = base64.b64encode(card_number_bytes).decode('utf-8')
            
            logging.info(f"Card number encoded to base64: {card_number_base64}")
            
            # Make API call to update the card number for the user
            try:
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                card_update_payload = {
                    "secret": card_number_base64
                }
                
                async with client.post(
                    f'https://api.printix.net/cloudprint/tenants/{tenant_id}/users/{user_id}/cards',
                    headers=headers,
                    json=card_update_payload
                ) as update_response:
                    if not update_response.ok:
                        logging.error(f"Failed to update card number. Status: {update_response.status}")
                        return func.HttpResponse(
                            body="Failed to update card number",
                            status_code=500
                        )
                    
                    logging.info("Card number updated successfully.")
                    
            except Exception as ex:
                logging.error(f"Failed to update card number: {str(ex)}")
                return func.HttpResponse(
                    body="Failed to update card number",
                    status_code=500
                )
            
            # Return success response with all gathered information
            return func.HttpResponse(
                body=json.dumps({
                    "userId": user_id,
                    "email": user_email,
                    "cardNumber": card_number,
                    "cardNumberBase64": card_number_base64,
                    "message": "Card number updated successfully"
                }),
                mimetype="application/json",
                status_code=200
            )

    except Exception as ex:
        logging.error(f"Unexpected error: {str(ex)}")
        return func.HttpResponse(
            body="Internal server error occurred.",
            status_code=500
        )