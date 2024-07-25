# SEC Mutual Funds Investment Monitor

## Project Description

This project involves creating a Flask web application that allows users to search and retrieve information about mutual fund investments from the SEC (U.S. Securities and Exchange Commission) website. The application integrates with the SEC's EDGAR database to provide detailed information on mutual fund investments, allowing users to monitor and analyze their portfolios.

## Features

### 1. Flask Application Setup

- **Basic Setup**: A robust Flask application framework has been created.
- **User Authentication**: Includes Signup and Login functionality with user session management.
- **Navigation Tabs**: Features intuitive tabs for easy navigation, including Home, Fund Search, Favorites, Monitor, and Profile sections.

### 2. Integration with SEC.gov

- **EDGAR Database Connection**: The project connects to the SEC's EDGAR database to fetch and display data related to mutual funds.
- **Search Functionality**: Users can search for mutual funds’ investments through the web interface.
- **Data Retrieval**: Retrieve detailed information about mutual funds, including submissions, holdings, and more.

### 3. User Features

- **Home Page**: View and search for mutual fund investments. The page displays well-known funds and RSS feed updates about the latest submissions from SEC.gov.
- **Fund Search**: Perform searches for mutual funds.
- **Monitor**: View information about the latest fund submissions, including a table of current fund positions and the ability to track how a fund's portfolio changes over the last five submissions. Users can understand whether a fund has maintained, added, or liquidated positions based on share amounts. Funds can be managed using radio buttons, with the fund list sourced from favorites.
- **Favorites**: Add and manage favorite funds for quick access.
- **Profile**: Update your profile information and manage your account.

**Note**: Users who are not logged in can access the Home and About pages. They can perform fund searches but cannot add to favorites or monitor funds. Users who sign up will gain full access to all features.

### 4. Data Visualization

- **Plot Generation**: Generate and save plots of historical stock prices for given ticker symbols.
- **RSS Feed Integration**: Fetch and display recent filings from SEC RSS feeds.

### 5. Admin Features

- **Admin Dashboard**: Special admin access for managing users and monitoring activities.
- **Admin Signup**: Secure admin signup with PIN validation.

### 6. Database

- **PostgreSQL**: The project uses PostgreSQL as the database for storing user information, mutual fund data, and other relevant information.

## Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/martynasfreitakas/FinalFinance.git
    cd FinalProject
    ```

2. **Create and activate a virtual environment**:
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate  # On Windows
    # For macOS/Linux, use: source .venv/bin/activate
    ```

3. **Navigate to the `FinalFinance` directory**:
    ```bash
    cd FinalFinance
    ```

4. **Install the dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

5. **Set up environment variables**:
    Create a `.env` file in the `FinalFinance` directory and add the following environment variables:
    ```env
    DATABASE_URL=postgresql://your_database_url
    SECRET_KEY=your_secret_key
    EMAIL_FOR_AUTHORIZATION=your_email_for_authorization
    USER_AGENT=your_user_agent
    ADMIN_PIN=your_admin_pin
    ```

6. **Run the application**:
    ```bash
    python run.py
    ```

## Usage

- **Home Page**: View and search for mutual fund investments. The page displays well-known funds and RSS feed updates about the latest submissions from SEC.gov.
- **Fund Search**: Perform searches for mutual funds.
- **Monitor**: View information about the latest fund submissions, including a table of current fund positions and track how a fund's portfolio changes over the last five submissions. Users can understand whether a fund has maintained, added, or liquidated positions based on share amounts. Manage fund information using radio buttons, with the fund list coming from favorites.
- **Favorites**: Add and manage favorite funds for quick access.
- **Profile**: Update your profile information and manage your account.

**Note**: Users who are not logged in can access the Home and About pages. They can perform fund searches but cannot add to favorites or monitor funds. Users who sign up will gain full access to all features.

## License

This project is available for use with the author's permission. Please contact the author for more information regarding usage and permissions.
