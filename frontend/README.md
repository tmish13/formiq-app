# FormIQ Frontend

The frontend application for FormIQ, an AI-powered exercise form analysis platform.

## Features

- User authentication (login/register)
- Dashboard with workout overview
- Real-time form analysis
- Workout tracking
- Progress monitoring
- Profile management

## Tech Stack

- React 18
- TypeScript
- Redux Toolkit
- React Router v6
- Styled Components
- Axios

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/formiq-app.git
cd formiq-app/frontend
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Create a `.env` file in the root directory and add the following variables:
```env
REACT_APP_API_URL=http://localhost:8000/api/v1
```

4. Start the development server:
```bash
npm start
# or
yarn start
```

The application will be available at `http://localhost:3000`.

## Project Structure

```
src/
├── components/         # Reusable UI components
│   ├── auth/          # Authentication components
│   ├── common/        # Common UI components
│   └── layout/        # Layout components
├── hooks/             # Custom React hooks
├── pages/             # Page components
├── services/          # API services
├── store/             # Redux store configuration
├── styles/            # Global styles and theme
└── types/             # TypeScript type definitions
```

## Available Scripts

- `npm start` - Runs the app in development mode
- `npm test` - Launches the test runner
- `npm run build` - Builds the app for production
- `npm run eject` - Ejects from Create React App

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 