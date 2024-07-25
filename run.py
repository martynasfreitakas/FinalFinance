from FinalFinance import create_app

# Create the Flask app using the create_app function
app = create_app()

if __name__ == '__main__':
    # Run the app in debug mode, accessible from any host
    app.run(debug=True, host="0.0.0.0")
