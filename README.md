Azure Function in Python. 
When printix will send a WebHook on a New user Create event, this function will 
a) get the userID 
b) Authorize to Printix API 
c) get users deails like name and email 
d) Lookup a file UserCardDetails.csv which is saved in Azure Storage-->Container-->File 
e) get card number from file, convert to base 64 
f) Update Printix user with the card number in base 64.

The Function is writtten in VS Code, the Microsoft recommend IDE for Azure Function Need to install "Azure Functions Core Tools" 
Supported Python, which at the time of this file is 3.11.X 
Printix Client ID, Printix Client Secret, and connection string , are saved as Enviornmental variables in Function Configuration.
