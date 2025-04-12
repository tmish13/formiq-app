import 'react-native-gesture-handler/jestSetup';
import '@testing-library/jest-native/extend-expect';

// Mock react-native-reanimated
jest.mock('react-native-reanimated', () => {
  const Reanimated = require('react-native-reanimated/mock');
  Reanimated.default.call = () => {};
  return Reanimated;
});

// Mock react-native
jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  RN.NativeModules.StatusBarManager = {
    getHeight: jest.fn(),
    setColor: jest.fn(),
    setStyle: jest.fn(),
    setHidden: jest.fn(),
  };
  return RN;
});

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock')
);

// Silence the warning: Animated: `useNativeDriver` is not supported
jest.mock('react-native/Libraries/Animated/NativeAnimatedHelper');

// Mock navigation
jest.mock('@react-navigation/native', () => {
  const actualNav = jest.requireActual('@react-navigation/native');
  return {
    ...actualNav,
    useNavigation: () => ({
      navigate: jest.fn(),
      goBack: jest.fn(),
    }),
    useRoute: () => ({
      params: {},
    }),
  };
});

// Set up global timing APIs
global.requestAnimationFrame = (callback) => setTimeout(callback, 0);
global.cancelAnimationFrame = jest.fn();

// Reset all mocks before each test
beforeEach(() => {
  jest.clearAllMocks();
});

// Mock react-native
jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  // Add any specific mocks here
  return {
    ...RN,
    Platform: {
      ...RN.Platform,
      OS: 'ios',
      select: jest.fn(obj => obj.ios),
    },
  };
});

// Mock react-native-gesture-handler
jest.mock('react-native-gesture-handler', () => {
  const { View } = require('react-native');
  return {
    PanGestureHandler: View,
    State: {},
    ScrollView: View,
    PanGestureHandlerGestureEvent: jest.fn(),
  };
});

// Global setup
global.window = {};
global.window = global; 