import requests

# Step 1: Set up the environment
BASE_URL = "https://services.leadconnectorhq.com/"
LOCATION_ID = "YOUR_LOCATION_ID_HERE"
API_KEY = "YOUR_API_KEY_HERE"

# Step 2: Authenticate with the API
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Version": "2021-07-28",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Step 3: Create a function to fetch messages
def fetch_contact_messages(contact_id, cursor=None, limit=100):
    url = f"{BASE_URL}conversations/search"

    payload = {"locationId": LOCATION_ID, "contactId": contact_id, "limit": limit}
    if cursor:
        payload["cursor"] = cursor

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# Step 4: Implement error handling and pagination
def get_all_contact_messages(contact_id):
    all_messages = []
    cursor = None

    while True:
        try:
            data = fetch_contact_messages(contact_id, cursor)
            messages = data.get("conversations", [])
            all_messages.extend(messages)

            cursor = data.get("meta", {}).get("cursor")
            if not cursor:
                break
        except requests.exceptions.RequestException as e:
            print(f"Error fetching messages: {e}")
            break

    return all_messages


# Step 5: Display or process the results
def main():
    contact_id = "CONTACT_ID_HERE"
    messages = get_all_contact_messages(contact_id)

    print(f"Total conversations fetched: {len(messages)}")
    for conversation in messages:
        print(f"Conversation ID: {conversation['id']}")
        print(f"Type: {conversation['type']}")
        print(f"Status: {conversation['status']}")
        print(f"Last Message: {conversation['lastMessage']}")
        print("---")


if __name__ == "__main__":
    main()
