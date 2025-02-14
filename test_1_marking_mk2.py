import unittest
import requests
import json
import csv
import random


class TestApi(unittest.TestCase):
    #with fastapi default port is 8000 with flask is 5000
    base_url = "http://127.0.0.1:8000"
    

    def populate_variables_from_csv(self):
        with open('read_from.csv', 'r') as f:
            reader = csv.reader(f)
            next(reader, None)
            data = [row for row in reader if len(row) >= 5]
            random_row = random.choice(data)
            return random_row

    def setUp(self):
        # populate data before each test by doing two POST
        self.id_shortened_url_1=""
        self.id_shortened_url_2=""
        
        self.url_to_shorten_1,self.url_to_shorten_2,self.url_after_update,self.not_existing_id,self.invalid_url=self.populate_variables_from_csv()
        
        def do_post(url_to_shorten):
            endpoint = "/"       
            print(url_to_shorten)
            url = f"{self.base_url}{endpoint}"   
            response = requests.post(url, json={'value': str(url_to_shorten)})
            self.assertEqual(response.status_code, 201, f"Expected status code 201, but got {response.status_code}")
            self.assertIsNotNone(response.text, "Response text should not be None.")
            response_extracted=response.json()
            id_returned=response_extracted["id"]#TODO add try catch / handle in case no id key was returned
            return id_returned
 
        self.id_shortened_url_1=do_post(self.url_to_shorten_1)
        print("id 1 obtained "+str(self.id_shortened_url_1))
        self.id_shortened_url_2=do_post(self.url_to_shorten_2)
        print("id 2 obtained "+str(self.id_shortened_url_2))
      

    def tearDown(self): #OK
        #erase everything
        endpoint = "/"
        url = f"{self.base_url}{endpoint}"
        response = requests.delete(url)
        #self.assertEqual(response.status_code, 404, f"Expected status code 404 to confirm correct erase, but got {response.status_code}")

    
    """
    /:id GET  
    Given an ID to the service, redirects the user to the matching long URL by returning 301 with the URL. 
    If the ID does not exist, 404 should be returned.
    """
    def test_get_request_with_id_expect_301(self):
        
        id = self.id_shortened_url_1
        expected_value = self.url_to_shorten_1

        endpoint = "/"
        url = f"{self.base_url}{endpoint}{id}"
        response = requests.get(url)
        
        self.assertEqual(response.status_code, 301, f"Expected status code 301, but got {response.status_code}")
        
        self.assertEqual(response.json().get("value"), expected_value, "Expected response body to be " +expected_value+" , but got "+response.json().get("value"))

    def test_get_request_with_id_expect_404(self):
        
        id = "Unseen_id" 

        endpoint = "/"
        url = f"{self.base_url}{endpoint}{id}"
        response = requests.get(url)
        
        self.assertEqual(response.status_code, 404, f"Expected status code 404, but got {response.status_code}")
    
    """
    /:id PUT 
    Updates the URL behind the given ID. To do so, in addition to the parameter in the URL, 
    the service requires additional information in the body of the request (e.g., encoded as JSON) 
    that contains the new version of the URL. Then, the function returns 200 if the update was successful, 400 with an error 
    if the update failed (e.g., the URL was invalid) or 404 if the ID does not exist.
    """
    def test_put_id(self):

        id = self.id_shortened_url_1
        url_to_update = self.id_shortened_url_1
        url_after_update = self.url_after_update
        not_existing_id = self.not_existing_id
        invalid_url = self.invalid_url


        endpoint = "/"
        url = f"{self.base_url}{endpoint}{id}"   
        response = requests.put(url, data=json.dumps({'url': url_after_update}))
        self.assertEqual(response.status_code, 200, f"Expected status code 200, but got {response.status_code}")

        #check value has been rally changed by doing a get
        url = f"{self.base_url}{endpoint}{id}"
        response = requests.get(url)
        self.assertEqual(response.json().get("value"), url_after_update, "Expected response body to be " +url_after_update+" , but got "+response.json().get("value"))

        
        #check 400 by passing invalid url
        url = f"{self.base_url}{endpoint}{id}"   
        response = requests.put(url, data=json.dumps({'url': invalid_url}))
        self.assertEqual(response.status_code, 400, f"Expected status code 400, but got {response.status_code}")

        #check 404 aka if id exists
        url = f"{self.base_url}{endpoint}{not_existing_id}"   
        response = requests.put(url, data=json.dumps({'url': not_existing_id}))
        self.assertEqual(response.status_code, 404, f"Expected status code 404, but got {response.status_code}")
        

    """
    /:id DELETE 
    Deletes the given short URL / ID and then returns 204. If the ID does not exist, returns 404
    """
    def test_deletion_id(self):
        #Erase ID
        endpoint = "/"
        id = self.id_shortened_url_1
        #url = f"{self.base_url}{endpoint}?value={id}"   
        url = f"{self.base_url}{endpoint}{id}"   
        response = requests.delete(url)   
        self.assertEqual(response.status_code, 204, f"Expected status code 204, but got {response.status_code}")
        response = requests.delete(url)
        self.assertEqual(response.status_code, 404, f"Expected status code 404, but got {response.status_code}")


    """
    / GET   
    Should return a list of something at the global level. Can either be a list of all keys (IDs), all long URLs, 
    or some combination of the two. Should return 200 on success, but the students can choose what to do on failure 
    (if applicable)
    """
    def test_get_all(self):
        endpoint = "/"        
        url = f"{self.base_url}{endpoint}"        
        response = requests.get(url)        
        self.assertEqual(response.status_code, 200, f"Expected status code 200, but got {response.status_code}")
        self.assertIsNotNone(response.text, "Response text should not be None.")
    

    """
    / POST    
    Should create a new short URL / ID for the given long URL (which must be given in the body). Returns a 201 with 
    the new ID on success, or a 400 if there was some failure (e.g., missing URL in body or URL was invalid).
    """
    def test_post(self):
        #add link 
        url_to_shorten="https://en.wikipedia.org/wiki/Docker_(software)"
        endpoint = "/"    

        
        url = f"{self.base_url}{endpoint}"   
        response = requests.post(url, json={'value': str(url_to_shorten)})

        
        self.assertEqual(response.status_code, 201, f"Expected status code 201, but got {response.status_code}")
        self.assertIsNotNone(response.json().get("id"), "Response text should not be None.")

        
        #check if id returned is correct
        temp=response.json().get("id")
        url = f"{self.base_url}{endpoint}{temp}"
        response = requests.get(url)
        self.assertEqual(response.status_code, 301, f"Expected status code 301, but got {response.status_code}")
        self.assertEqual(response.json().get("value"), url_to_shorten, "Expected response body to be " +url_to_shorten+" , but got "+response.json().get("value"))


        #try error by passing an empty link
        url_to_shorten=""
        endpoint = "/"       
        url = f"{self.base_url}{endpoint}{url_to_shorten}"   
        response = requests.post(url, json={'value': str(url_to_shorten)})
        self.assertEqual(response.status_code, 400, f"Expected status code 400, but got {response.status_code}")
       
        
    """
    / DELETE    
    Deletes all ID/URL pairs in the service.
    """
    def test_deletion_all(self):
        #delete all
        endpoint = "/"       
        url = f"{self.base_url}{endpoint}"   
        response = requests.delete(url)
        self.assertEqual(response.status_code, 404, f"Expected status code 404 to confirm correct erase, but got {response.status_code}")

        #make a getall to check that stuff is erased
        endpoint = "/"
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url)
        self.assertIsNone(response.json().get("value"), "The value should be None since should be empty.")


if __name__ == '__main__':
    unittest.main()