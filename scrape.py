from datetime import datetime
import requests
import boto3

key = '0GDGIbY1c_IZZC_TY0DTcUp01OZcdvYJrH22haUHfyJ8ZgA0892MaoN0r9n_vwn-_80duthilMpyJJ6ZE8_H5VF5RGF1eOlZ9uFMWsC1oSpY-yPU6k_NxNuyj_UqZXYx'
dynamodb = boto3.client('dynamodb', region_name='us-east-1')

def query_yelp(term, location, limit=50):
    url = 'https://api.yelp.com/v3/businesses/search'
    headers = {
        'Authorization': f'Bearer {key}',
    }
    offset = 0
    total = 1000
    results = []
    while offset < total and offset < 1000:
        print("Querying, offset: ", offset, " total: ", total)
        params = {
            'term': term,
            'location': location,
            'limit': limit,
            'offset': offset,
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            businesses = response.json().get('businesses', [])
            if not businesses:
                break
            results += businesses
            offset += limit
            total = response.json().get('total', 0)
            # total = len(results)
            # return response.json().get('businesses', [])
        else:
            print(response.text)
            print(f"Failed to query Yelp API {response.status_code}")
            break
    return results

def dynamo(data, table, cuisine):
    timestamp = datetime.now().isoformat()
    for restaurant in data:
        item = {
            'BusinessID': {'S': restaurant['id']},
            'Name': {'S': restaurant['name']},
            'Address': {'S': restaurant['location']['address1']},
            'Coordinates': {'S': f"{restaurant['coordinates']['latitude']},{restaurant['coordinates']['longitude']}"},
            'NumberOfReviews': {'N': str(restaurant['review_count'])},
            'Rating': {'N': str(restaurant['rating'])},
            'ZipCode': {'S': restaurant['location']['zip_code']},
            'InsertedAtTimestamp': {'S': timestamp},
            'Cuisine': {'S': cuisine},
        }
        # print(item)
        try:
            dynamodb.put_item(TableName = table, Item = item)
        except:
            print("Failed to insert into DynamoDB")

location = 'Manhattan, New York'
# Query Chinese restaurants - do pagination querying 50 at a time
chinese_data = query_yelp('Chinese', location, limit=50)
print(f"Total restaurants retrieved: {len(chinese_data)}")
dynamo(chinese_data, 'yelp-restaurants', 'chinese')
print(f"Inserted {len(chinese_data)} rows of Chinese restaurants")

# Query Indian restaurants
indian_data = query_yelp('Indian', location, limit=50)
print(f"Total restaurants retrieved: {len(indian_data)}")
dynamo(indian_data, 'yelp-restaurants', 'indian')
print(f"Inserted {len(indian_data)} rows of Indian restaurants")

# Query Italian restaurants
italian_data = query_yelp('Italian', location, limit=50)
print(f"Total restaurants retrieved: {len(italian_data)}")
dynamo(italian_data, 'yelp-restaurants', 'italian')
print(f"Inserted {len(italian_data)} rows of Italian restaurants")