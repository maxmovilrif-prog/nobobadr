import requests
import sys
import json
from datetime import datetime

class GlovoAlgecirasAPITester:
    def __init__(self, base_url="https://algeciras-courier.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}  # Store tokens for different user types
        self.test_data = {}  # Store created test data
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, params=params)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"   Response: {response.json()}")
                except:
                    print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_user_registration_and_login(self):
        """Test user registration and login for all 3 roles"""
        print("\n" + "="*50)
        print("TESTING USER AUTHENTICATION")
        print("="*50)
        
        timestamp = datetime.now().strftime('%H%M%S')
        
        # Test data for different user types
        users = [
            {
                'role': 'customer',
                'email': f'customer_{timestamp}@test.com',
                'name': 'Test Customer',
                'phone': '+34600123456',
                'password': 'TestPass123!'
            },
            {
                'role': 'driver',
                'email': f'driver_{timestamp}@test.com',
                'name': 'Test Driver',
                'phone': '+34600123457',
                'password': 'TestPass123!',
                'vehicle_type': 'motorcycle'
            },
            {
                'role': 'business',
                'email': f'business_{timestamp}@test.com',
                'name': 'Test Business Owner',
                'phone': '+34600123458',
                'password': 'TestPass123!'
            }
        ]

        for user_data in users:
            role = user_data['role']
            
            # Test registration
            success, response = self.run_test(
                f"Register {role}",
                "POST",
                "auth/register",
                200,
                data=user_data
            )
            
            if not success:
                print(f"❌ Registration failed for {role}, skipping login")
                continue

            # Test login
            success, login_response = self.run_test(
                f"Login {role}",
                "POST",
                "auth/login",
                200,
                data={
                    "email": user_data['email'],
                    "password": user_data['password']
                }
            )
            
            if success and 'token' in login_response:
                self.tokens[role] = login_response['token']
                self.test_data[f'{role}_user'] = login_response['user']
                print(f"✅ {role.capitalize()} token stored successfully")
                
                # Test /auth/me endpoint
                self.run_test(
                    f"Get {role} profile",
                    "GET",
                    "auth/me",
                    200,
                    token=self.tokens[role]
                )
            else:
                print(f"❌ Login failed for {role}")

    def test_business_operations(self):
        """Test business creation and management"""
        print("\n" + "="*50)
        print("TESTING BUSINESS OPERATIONS")
        print("="*50)
        
        if 'business' not in self.tokens:
            print("❌ No business token available, skipping business tests")
            return

        # Create business
        business_data = {
            "name": "Test Restaurant Algeciras",
            "category": "restaurant",
            "description": "Un restaurante de prueba en Algeciras",
            "address": "Calle Test 123, Algeciras",
            "phone": "+34956123456",
            "image_url": "https://via.placeholder.com/400x300",
            "delivery_time": "30-45 min"
        }

        success, response = self.run_test(
            "Create Business",
            "POST",
            "businesses",
            200,
            data=business_data,
            token=self.tokens['business']
        )

        if success and 'id' in response:
            self.test_data['business'] = response
            business_id = response['id']
            
            # Test get all businesses
            self.run_test(
                "Get All Businesses",
                "GET",
                "businesses",
                200
            )
            
            # Test get business by ID
            self.run_test(
                "Get Business by ID",
                "GET",
                f"businesses/{business_id}",
                200
            )
            
            # Test get businesses by category
            self.run_test(
                "Get Businesses by Category",
                "GET",
                "businesses",
                200,
                params={"category": "restaurant"}
            )

    def test_product_operations(self):
        """Test product creation and management"""
        print("\n" + "="*50)
        print("TESTING PRODUCT OPERATIONS")
        print("="*50)
        
        if 'business' not in self.tokens or 'business' not in self.test_data:
            print("❌ No business available, skipping product tests")
            return

        business_id = self.test_data['business']['id']
        
        # Create products
        products = [
            {
                "business_id": business_id,
                "name": "Pizza Margherita",
                "description": "Pizza clásica con tomate, mozzarella y albahaca",
                "price": 12.50,
                "image_url": "https://via.placeholder.com/300x200",
                "category": "Pizza"
            },
            {
                "business_id": business_id,
                "name": "Coca Cola",
                "description": "Refresco de cola 330ml",
                "price": 2.50,
                "image_url": "https://via.placeholder.com/300x200",
                "category": "Bebidas"
            }
        ]

        created_products = []
        for product_data in products:
            success, response = self.run_test(
                f"Create Product: {product_data['name']}",
                "POST",
                "products",
                200,
                data=product_data,
                token=self.tokens['business']
            )
            
            if success and 'id' in response:
                created_products.append(response)

        if created_products:
            self.test_data['products'] = created_products
            
            # Test get products for business
            self.run_test(
                "Get Products for Business",
                "GET",
                f"products/{business_id}",
                200
            )

    def test_order_operations(self):
        """Test order creation and management"""
        print("\n" + "="*50)
        print("TESTING ORDER OPERATIONS")
        print("="*50)
        
        if 'customer' not in self.tokens or 'products' not in self.test_data:
            print("❌ No customer token or products available, skipping order tests")
            return

        # Create order
        order_data = {
            "business_id": self.test_data['business']['id'],
            "items": [
                {
                    "product_id": self.test_data['products'][0]['id'],
                    "product_name": self.test_data['products'][0]['name'],
                    "quantity": 2,
                    "price": self.test_data['products'][0]['price']
                },
                {
                    "product_id": self.test_data['products'][1]['id'],
                    "product_name": self.test_data['products'][1]['name'],
                    "quantity": 1,
                    "price": self.test_data['products'][1]['price']
                }
            ],
            "delivery_address": "Calle Entrega 456, Algeciras"
        }

        success, response = self.run_test(
            "Create Order",
            "POST",
            "orders",
            200,
            data=order_data,
            token=self.tokens['customer']
        )

        if success and 'id' in response:
            self.test_data['order'] = response
            order_id = response['id']
            
            # Test get orders for customer
            self.run_test(
                "Get Customer Orders",
                "GET",
                "orders",
                200,
                token=self.tokens['customer']
            )
            
            # Test get orders for business
            self.run_test(
                "Get Business Orders",
                "GET",
                "orders",
                200,
                token=self.tokens['business']
            )
            
            # Test get specific order
            self.run_test(
                "Get Order by ID",
                "GET",
                f"orders/{order_id}",
                200,
                token=self.tokens['customer']
            )

    def test_driver_operations(self):
        """Test driver-specific operations"""
        print("\n" + "="*50)
        print("TESTING DRIVER OPERATIONS")
        print("="*50)
        
        if 'driver' not in self.tokens:
            print("❌ No driver token available, skipping driver tests")
            return

        # Test update availability
        self.run_test(
            "Update Driver Availability - Available",
            "PATCH",
            "drivers/availability",
            200,
            params={"is_available": True},
            token=self.tokens['driver']
        )
        
        # Test get available orders
        self.run_test(
            "Get Available Orders",
            "GET",
            "drivers/available-orders",
            200,
            token=self.tokens['driver']
        )
        
        # Test get driver orders
        self.run_test(
            "Get Driver Orders",
            "GET",
            "orders",
            200,
            token=self.tokens['driver']
        )

    def test_order_status_updates(self):
        """Test order status updates"""
        print("\n" + "="*50)
        print("TESTING ORDER STATUS UPDATES")
        print("="*50)
        
        if 'order' not in self.test_data:
            print("❌ No order available, skipping status update tests")
            return

        order_id = self.test_data['order']['id']
        
        # Business accepts order
        if 'business' in self.tokens:
            self.run_test(
                "Business Update Order Status - Preparing",
                "PATCH",
                f"orders/{order_id}/status",
                200,
                data={"status": "preparing"},
                token=self.tokens['business']
            )
        
        # Driver assigns to order
        if 'driver' in self.tokens:
            self.run_test(
                "Driver Assign to Order",
                "POST",
                f"orders/{order_id}/assign-driver",
                200,
                token=self.tokens['driver']
            )

    def test_payment_operations(self):
        """Test payment operations"""
        print("\n" + "="*50)
        print("TESTING PAYMENT OPERATIONS")
        print("="*50)
        
        if 'customer' not in self.tokens or 'order' not in self.test_data:
            print("❌ No customer token or order available, skipping payment tests")
            return

        order_id = self.test_data['order']['id']
        
        # Test create checkout session
        success, response = self.run_test(
            "Create Checkout Session",
            "POST",
            f"payments/create-checkout?order_id={order_id}",
            200,
            token=self.tokens['customer']
        )
        
        if success and 'session_id' in response:
            session_id = response['session_id']
            
            # Test get payment status
            self.run_test(
                "Get Payment Status",
                "GET",
                f"payments/status/{session_id}",
                200,
                token=self.tokens['customer']
            )

    def test_chat_operations(self):
        """Test chat/messaging operations"""
        print("\n" + "="*50)
        print("TESTING CHAT OPERATIONS")
        print("="*50)
        
        if 'customer' not in self.tokens or 'order' not in self.test_data:
            print("❌ No customer token or order available, skipping chat tests")
            return

        order_id = self.test_data['order']['id']
        
        # Send message from customer
        success, response = self.run_test(
            "Send Message from Customer",
            "POST",
            "messages",
            200,
            data={
                "order_id": order_id,
                "message": "¿Cuánto tiempo tardará mi pedido?"
            },
            token=self.tokens['customer']
        )
        
        # Send message from driver (if available)
        if 'driver' in self.tokens:
            self.run_test(
                "Send Message from Driver",
                "POST",
                "messages",
                200,
                data={
                    "order_id": order_id,
                    "message": "Estoy en camino, llegaré en 10 minutos"
                },
                token=self.tokens['driver']
            )
        
        # Get messages for order
        self.run_test(
            "Get Messages for Order",
            "GET",
            f"messages/{order_id}",
            200,
            token=self.tokens['customer']
        )

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Glovo Algeciras API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        
        # Test authentication first
        self.test_user_registration_and_login()
        
        # Test business operations
        self.test_business_operations()
        
        # Test product operations
        self.test_product_operations()
        
        # Test order operations
        self.test_order_operations()
        
        # Test driver operations
        self.test_driver_operations()
        
        # Test order status updates
        self.test_order_status_updates()
        
        # Test payment operations
        self.test_payment_operations()
        
        # Test chat operations
        self.test_chat_operations()
        
        # Print final results
        print("\n" + "="*60)
        print("FINAL TEST RESULTS")
        print("="*60)
        print(f"📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        print(f"📈 Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed")
            return 1

def main():
    tester = GlovoAlgecirasAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())