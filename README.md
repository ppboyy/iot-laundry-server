# IoT Laundry Server

Backend server for IoT laundry system that connects AWS RDS database to your Vercel frontend.

## Features

- Express.js REST API server
- Support for both MySQL and PostgreSQL RDS instances
- CORS configured for Vercel frontend
- Connection pooling for optimal performance
- Error handling and logging
- Health check endpoint

## Prerequisites

- Node.js (v14 or higher)
- AWS RDS database (MySQL or PostgreSQL)
- Database credentials and endpoint

## Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment variables:**
   
   Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
   
   Edit `.env` and add your AWS RDS credentials:
   ```env
   PORT=3000
   NODE_ENV=development
   
   # Choose your database type
   DB_TYPE=mysql  # or "postgres"
   DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
   DB_PORT=3306   # 3306 for MySQL, 5432 for PostgreSQL
   DB_USER=your_db_username
   DB_PASSWORD=your_db_password
   DB_NAME=your_database_name
   
   # Add your Vercel frontend URL
   ALLOWED_ORIGINS=https://your-app.vercel.app
   ```

## Database Setup

The example routes assume the following tables exist. Modify according to your schema:

```sql
-- Example MySQL schema
CREATE TABLE machines (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'idle',
    location VARCHAR(255)
);

CREATE TABLE machine_status (
    id INT PRIMARY KEY AUTO_INCREMENT,
    machine_id INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    temperature DECIMAL(5,2),
    cycle_time INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(id)
);
```

## Running the Server

**Development mode (with auto-restart):**
```bash
npm run dev
```

**Production mode:**
```bash
npm start
```

The server will start on `http://localhost:3000` (or your configured PORT).

## API Endpoints

### Health Check
- `GET /health` - Check if server is running

### Machines
- `GET /api/machines` - Get all machines
- `GET /api/machines/:id` - Get specific machine by ID
- `GET /api/machines/:id/status` - Get latest status for a machine

### Status
- `GET /api/status` - Get recent status logs (last 100)
- `POST /api/status` - Record new machine status

### Dashboard
- `GET /api/dashboard` - Get summary statistics

### Example Response
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Washer A",
      "status": "running",
      "location": "Floor 1"
    }
  ],
  "count": 1
}
```

## Connecting to Vercel Frontend

In your Vercel frontend, fetch data using:

```javascript
// Example React/Next.js code
const fetchMachines = async () => {
  try {
    const response = await fetch('http://your-server-url:3000/api/machines');
    const result = await response.json();
    
    if (result.success) {
      console.log(result.data);
    }
  } catch (error) {
    console.error('Error fetching machines:', error);
  }
};
```

## Deployment Options

### Option 1: Deploy to AWS EC2
1. Launch an EC2 instance
2. Install Node.js
3. Clone your repository
4. Set up environment variables
5. Run with PM2 for process management:
   ```bash
   npm install -g pm2
   pm2 start server.js --name iot-laundry-server
   ```

### Option 2: Deploy to Heroku
1. Create Heroku app
2. Set environment variables in Heroku dashboard
3. Deploy via Git:
   ```bash
   git push heroku main
   ```

### Option 3: Deploy to AWS Elastic Beanstalk
1. Install EB CLI
2. Initialize: `eb init`
3. Create environment: `eb create`
4. Deploy: `eb deploy`

## Security Considerations

- ✅ Never commit `.env` file to version control
- ✅ Use environment variables for sensitive data
- ✅ Configure CORS to only allow your Vercel domain
- ✅ Use AWS security groups to restrict RDS access
- ✅ Consider using AWS Secrets Manager for credentials
- ✅ Enable SSL/TLS for database connections in production

## Customization

Edit `routes/api.js` to add custom endpoints based on your database schema and business logic.

## Troubleshooting

**Connection Failed:**
- Verify RDS security group allows inbound traffic from your server IP
- Check database credentials in `.env`
- Ensure RDS instance is publicly accessible (if needed)

**CORS Errors:**
- Add your Vercel domain to `ALLOWED_ORIGINS` in `.env`
- Ensure frontend is making requests to the correct server URL

## License

ISC
