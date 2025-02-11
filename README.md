# Azure Function for Printix WebHook Integration

Azure Function in Python  

When Printix sends a WebHook on a **New User Create** event, this function will:  

1. Get the `userID`  
2. Authorize to **Printix API**  
3. Get user details like **name** and **email**  
4. Look up a file **UserCardDetails.csv** which is saved in:  
   - **Azure Storage** → **Container** → **File**  
5. Get **card number** from the file, convert it to **Base64**  
6. Update **Printix user** with the **card number** in Base64  

## Development Setup  

- The function is written in **VS Code**, the **Microsoft-recommended IDE** for **Azure Functions**  
- Install **Azure Functions Core Tools**  
- Supported **Python version**: **3.11.X** (as of this file's creation)  

## Environment Variables  

- **PRINTIX_CLIENT_ID**  
- **PRINTIX_CLIENT_SECRET**  
- **CONNECTION_STRING**  

These are saved as **environment variables** in **Azure Function Configuration**  

