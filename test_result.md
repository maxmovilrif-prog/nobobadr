#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Nubo is a multi-service marketplace application for España, Europa y Marruecos. The app includes:
  - Food delivery, grocery shopping, package delivery
  - Courier services (MRW, Correos Express, NACEX, GLS)
  - Vehicle marketplace with advanced search/filters
  - Dropshipping from Alibaba, Temu, AliExpress with 15-25% commission
  - Electronics marketplace
  - NuboRide (Uber-like transport service)
  - PWA with offline capabilities
  - Google Maps integration for real-time tracking and routes
  
  Current tasks:
  1. Update contact email from contacto@nubo.com to exprenobo@hotmail.com
  2. Verify Google Maps integration for NuboRide and delivery tracking
  3. Complete dropshipping business dashboard integration
  4. Test all features end-to-end

backend:
  - task: "User authentication (JWT)"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "JWT authentication implemented with login, register, and me endpoints"
  
  - task: "Dropshipping API endpoints"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Dropshipping endpoints exist: POST /api/dropshipping/products, GET /api/dropshipping/products, GET /api/dropshipping/orders-to-purchase. Need to test functionality."
  
  - task: "Google Maps coordinates storage in orders"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Orders support coordinates for pickup and delivery locations"

frontend:
  - task: "Contact email update"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/components/Footer.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Updated email from contacto@nubo.com to exprenobo@hotmail.com in Footer.js"
  
  - task: "Google Maps integration components"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/components/MapComponent.js, /app/frontend/src/components/RouteSelector.js, /app/frontend/src/components/RideBooking.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "MapComponent, RouteSelector, and RideBooking components exist and use REACT_APP_GOOGLE_MAPS_API_KEY. Need to verify integration in CustomerDashboard."
  
  - task: "Dropshipping panel integration"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/DropshippingPanel.js, /app/frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "DropshippingPanel.js now imported in App.js and routed at /dropshipping-panel for business users. Added navigation button in BusinessDashboard header."
  
  - task: "NuboRide integration with RideBooking"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/CustomerDashboard.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "RideBooking component integrated in CustomerDashboard. Opens when transport/NuboRide business is selected. Added handleRideBooking function to process ride orders."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 0
  run_ui: false

test_plan:
  current_focus:
    - "Test dropshipping endpoints and panel functionality"
    - "Test NuboRide booking flow with RouteSelector"
    - "Verify Google Maps integration (note: API key is placeholder)"
    - "Test backend authentication and order creation"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Phase 1 complete: Email updated, DropshippingPanel routed, NuboRide integrated. IMPORTANT: Google Maps API key is set to placeholder 'YOUR_API_KEY_HERE' - maps will not work without valid key. Ready for backend testing."