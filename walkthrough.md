# SaveBasket Implementation Walkthrough

We have successfully initialized and built the foundation of the **SaveBasket** platform, including a Django backend connected to PostgreSQL (with local SQLite fallback) and a Flutter cross-platform mobile frontend.

---

## 🛠️ What Was Built

### 1. Django Backend Component
We created three main local Django applications:
- **`supermarkets`**: Houses `Supermarket` and `Branch` models with latitude, longitude, and address fields to support spatial mapping.
- **`products`**: Defines `Product` (featuring categories, SKU/barcode fields) and `ProductPrice` (representing real-time branch-specific pricing).
- **`baskets`**: Defines `Basket` and `BasketItem` models, including an optimized pricing comparison routine (`compare_prices`) that runs database-level aggregations to compare, sort, and rank branches based on total cost and item completeness.

Other backend details:
- **Environment config**: Set up `.env` loading for seamless integration with Supabase/PostgreSQL, falling back to SQLite for local development.
- **REST APIs**: Built serializers and viewsets using Django REST Framework for clean REST CRUD endpoints under `/api/`.
- **Database Seeder**: Added a custom Django command `python manage.py seed_data` that prepopulates the database with real-world Kenyan supermarkets (Carrefour, Naivas, Quickmart) and typical items (Brookside Milk, Kabras Sugar, Jogoo Maize Meal) at different prices.
- **Testing**: Added unit test coverage for the basket optimization logic.

---

### 2. Flutter Frontend Component
Created a responsive, Material 3 styled Flutter client located in the `frontend/` directory:
- **State Management**: Implemented `BasketProvider` utilizing Flutter's `ChangeNotifier` to maintain the active list, search results, and comparison stats reactively.
- **API Client**: Implemented `ApiService` configured with dynamic URL mapping (handling standard Android emulator redirects to localhost).
- **Premium Tabbed UI**:
  - **Dashboard**: Features an optimized forest green design showing quick stats (current cheapest store, total basket items) and live savings calculation tips.
  - **Browse**: Features an interactive search bar with instant queries, brand filtering, and quantity modifiers to easily add groceries.
  - **My Basket**: Lists active groceries with increment/decrement buttons and displays a horizontal slider of live comparison cards. Cards adapt color and badges (e.g. "Best Deal", "Incomplete") dynamically based on completeness and total cost.
  - **Breakdown Details**: Provides a detailed bottom-sheet style checkout preview of item availability and totals.

---

## 🧪 Validation & Verification

### 1. Backend Unit Tests
We verified the pricing comparison logic by executing:
```bash
python manage.py test
```
Result: **2 tests passed successfully (0.007 seconds)**. The optimizer correctly ranked cheaper stores first and handled missing product situations:
```text
Found 2 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
..
Ran 2 tests in 0.007s
OK
```

### 2. Flutter Code Analysis
We ran static code analysis on the Flutter frontend:
```bash
flutter analyze
```
Result: **No issues found (10.9 seconds)**. All Dart class files are clean, free of compile errors, and correctly typed.

### 3. Database Seeding
Ran the seeder successfully:
```bash
python manage.py seed_data
```
Result: **Database seeded with Carrefour, Naivas, and Quickmart branches and products**.

---

## 🚀 How to Run Locally

### Step 1: Run the Django Backend
1. Navigate to the `backend/` directory.
2. Start the development server:
   ```bash
   python manage.py runserver
   ```
   *The backend will be available at `http://127.0.0.1:8000/api/`.*

### Step 2: Run the Flutter App
1. Navigate to the `frontend/` directory.
2. Launch the application:
   ```bash
   flutter run
   ```
   *(Supports Android, iOS, Chrome/Web, and Desktop).*
