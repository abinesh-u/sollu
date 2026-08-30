import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# The exact scopes we requested in the Google Cloud Console
SCOPES = [
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/tasks'
]

def authenticate():
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("Starting browser login flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("Success! token.json has been generated.")
    else:
        print("token.json is already valid.")

    print("\n--- REFRESH TOKEN ---")
    print("Add this to Secret Manager as sollu-google-refresh-token (Tier 2 setup) or GOOGLE_REFRESH_TOKEN in .env (Tier 1 setup)")
    print(creds.refresh_token)
    print("---------------------\n")

if __name__ == '__main__':
    authenticate()
