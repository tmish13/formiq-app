/**
 * Consolidated Tests for Subscription Management
 * 
 * This file tests user interactions with subscription features:
 * 1. Viewing available subscription plans
 * 2. Managing current subscription
 * 3. Upgrading or downgrading subscription
 * 4. Canceling subscription and handling renewal
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { http, HttpResponse } from 'msw';

// Import shared testing utilities
import { 
  setupMockServer, 
  setupServerLifecycle,
  createMockSubscription,
  createMockSubscriptionPlan,
  createMockSubscriptionPlans,
  subscriptionHandlers
} from '../utils/sharedMocks';

// Setup mock server with shared handlers
const server = setupMockServer([...subscriptionHandlers]);
setupServerLifecycle(server);

/**
 * Subscription Management Tests
 */
describe('Subscription Management User Interactions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });
  
  /**
   * Component for viewing subscription plans
   */
  const SubscriptionPlans = () => {
    const [plans, setPlans] = React.useState<any[]>([]);
    const [isLoading, setIsLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);
    const [selectedPlan, setSelectedPlan] = React.useState<string | null>(null);
    const [checkoutUrl, setCheckoutUrl] = React.useState<string | null>(null);
    
    React.useEffect(() => {
      const fetchPlans = async () => {
        try {
          const response = await fetch('/api/subscription/plans');
          const data = await response.json();
          setPlans(data);
        } catch (err) {
          setError('Failed to load subscription plans');
        } finally {
          setIsLoading(false);
        }
      };
      
      fetchPlans();
    }, []);
    
    const handleSelectPlan = (planId: string) => {
      setSelectedPlan(planId);
    };
    
    const handleSubscribe = async () => {
      if (!selectedPlan) return;
      
      setIsLoading(true);
      setError(null);
      
      try {
        const response = await fetch('/api/subscription/checkout', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ planId: selectedPlan })
        });
        
        const data = await response.json();
        setCheckoutUrl(data.url);
      } catch (err) {
        setError('Failed to create checkout session');
      } finally {
        setIsLoading(false);
      }
    };
    
    if (isLoading && plans.length === 0) {
      return <div data-testid="loading">Loading subscription plans...</div>;
    }
    
    if (error) {
      return <div data-testid="error" role="alert">{error}</div>;
    }
    
    return (
      <div>
        <h1>Choose Your Subscription Plan</h1>
        
        <div className="plans-container" data-testid="plans-container">
          {plans.map(plan => (
            <div 
              key={plan.id} 
              className={`plan ${selectedPlan === plan.id ? 'selected' : ''} ${plan.isPopular ? 'popular' : ''}`}
              data-testid={`plan-${plan.id}`}
            >
              {plan.isPopular && <div className="popular-badge">Most Popular</div>}
              
              <h2>{plan.name}</h2>
              <div className="price">
                ${plan.price} <span className="interval">/{plan.interval}</span>
              </div>
              
              <ul className="features">
                {plan.features.map((feature: string, index: number) => (
                  <li key={index}>{feature}</li>
                ))}
              </ul>
              
              <button
                onClick={() => handleSelectPlan(plan.id)}
                className={selectedPlan === plan.id ? 'selected' : ''}
                data-testid={`select-plan-${plan.id}`}
              >
                {selectedPlan === plan.id ? 'Selected' : 'Select Plan'}
              </button>
            </div>
          ))}
        </div>
        
        {selectedPlan && (
          <div className="checkout-section">
            <button 
              onClick={handleSubscribe} 
              disabled={isLoading}
              data-testid="subscribe-button"
            >
              {isLoading ? 'Processing...' : 'Subscribe Now'}
            </button>
          </div>
        )}
        
        {checkoutUrl && (
          <div data-testid="checkout-redirect">
            <p>Redirecting to checkout...</p>
            <a href={checkoutUrl} data-testid="checkout-link">
              Click here if you're not redirected automatically
            </a>
          </div>
        )}
      </div>
    );
  };
  
  /**
   * Component for managing existing subscription
   */
  const SubscriptionManager = () => {
    const [subscription, setSubscription] = React.useState<any | null>(null);
    const [plans, setPlans] = React.useState<any[]>([]);
    const [selectedPlan, setSelectedPlan] = React.useState<string | null>(null);
    const [isLoading, setIsLoading] = React.useState(true);
    const [isProcessing, setIsProcessing] = React.useState(false);
    const [error, setError] = React.useState<string | null>(null);
    const [message, setMessage] = React.useState<string | null>(null);
    
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Fetch current subscription
        const subscriptionResponse = await fetch('/api/subscription/current');
        const subscriptionData = await subscriptionResponse.json();
        setSubscription(subscriptionData);
        
        // Fetch available plans
        const plansResponse = await fetch('/api/subscription/plans');
        const plansData = await plansResponse.json();
        setPlans(plansData);
      } catch (err) {
        setError('Failed to load subscription data');
      } finally {
        setIsLoading(false);
      }
    };
    
    React.useEffect(() => {
      fetchData();
    }, []);
    
    const getCurrentPlanDetails = () => {
      if (!subscription || !plans.length) return null;
      return plans.find(plan => plan.id === subscription.planId);
    };
    
    const formatDate = (dateString: string) => {
      return new Date(dateString).toLocaleDateString();
    };
    
    const handleToggleAutoRenew = async () => {
      if (!subscription) return;
      
      setIsProcessing(true);
      setError(null);
      setMessage(null);
      
      try {
        const response = await fetch(`/api/subscription/${subscription.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            autoRenew: !subscription.autoRenew,
            cancelAtPeriodEnd: subscription.autoRenew
          })
        });
        
        const data = await response.json();
        setSubscription(data);
        setMessage(
          data.autoRenew ? 
            'Your subscription will automatically renew' : 
            'Your subscription will expire at the end of the current period'
        );
      } catch (err) {
        setError('Failed to update auto-renew setting');
      } finally {
        setIsProcessing(false);
      }
    };
    
    const handleCancelSubscription = async () => {
      if (!subscription) return;
      
      if (!window.confirm('Are you sure you want to cancel your subscription?')) {
        return;
      }
      
      setIsProcessing(true);
      setError(null);
      setMessage(null);
      
      try {
        const response = await fetch(`/api/subscription/${subscription.id}/cancel`, {
          method: 'POST'
        });
        
        const data = await response.json();
        setSubscription(data);
        setMessage('Your subscription has been canceled');
      } catch (err) {
        setError('Failed to cancel subscription');
      } finally {
        setIsProcessing(false);
      }
    };
    
    const handleChangePlan = async () => {
      if (!selectedPlan || !subscription) return;
      
      setIsProcessing(true);
      setError(null);
      setMessage(null);
      
      const endpointSuffix = 
        getCurrentPlanDetails()?.price < plans.find(p => p.id === selectedPlan)?.price
          ? 'upgrade'
          : 'downgrade';
      
      try {
        const response = await fetch(`/api/subscription/${endpointSuffix}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ planId: selectedPlan })
        });
        
        const data = await response.json();
        setSubscription(data.subscription);
        setMessage(data.message || 'Your subscription has been updated');
        setSelectedPlan(null);
      } catch (err) {
        setError('Failed to change subscription plan');
      } finally {
        setIsProcessing(false);
      }
    };
    
    if (isLoading) {
      return <div data-testid="loading">Loading your subscription...</div>;
    }
    
    if (error) {
      return <div data-testid="error" role="alert">{error}</div>;
    }
    
    if (!subscription) {
      return (
        <div data-testid="no-subscription">
          <p>You don't have an active subscription</p>
          <button onClick={() => window.location.href = '/subscription/plans'}>
            View Subscription Plans
          </button>
        </div>
      );
    }
    
    const currentPlan = getCurrentPlanDetails();
    
    return (
      <div data-testid="subscription-manager">
        <h1>Manage Your Subscription</h1>
        
        {message && (
          <div className="message" data-testid="success-message">
            {message}
          </div>
        )}
        
        <div className="current-plan" data-testid="current-plan">
          <h2>Current Plan: {currentPlan?.name}</h2>
          <p>Status: <span data-testid="subscription-status">{subscription.status}</span></p>
          <p>
            Period: {formatDate(subscription.currentPeriodStart)} - {formatDate(subscription.currentPeriodEnd)}
          </p>
          <p>Auto-renew: <span data-testid="auto-renew-status">{subscription.autoRenew ? 'Yes' : 'No'}</span></p>
        </div>
        
        <div className="subscription-actions">
          <button
            onClick={handleToggleAutoRenew}
            disabled={isProcessing || subscription.status !== 'active'}
            data-testid="toggle-auto-renew"
          >
            {subscription.autoRenew ? 'Disable Auto-Renew' : 'Enable Auto-Renew'}
          </button>
          
          {subscription.status === 'active' && (
            <button
              onClick={handleCancelSubscription}
              disabled={isProcessing}
              data-testid="cancel-subscription"
            >
              Cancel Subscription
            </button>
          )}
        </div>
        
        <div className="change-plan">
          <h2>Change Your Plan</h2>
          
          <div className="plan-options">
            {plans.map(plan => (
              <div key={plan.id} className="plan-option">
                <input
                  type="radio"
                  id={`plan-option-${plan.id}`}
                  name="plan"
                  value={plan.id}
                  checked={selectedPlan === plan.id}
                  onChange={() => setSelectedPlan(plan.id)}
                  disabled={plan.id === subscription.planId}
                  data-testid={`plan-option-${plan.id}`}
                />
                <label htmlFor={`plan-option-${plan.id}`}>
                  {plan.name} - ${plan.price}/{plan.interval}
                </label>
              </div>
            ))}
          </div>
          
          {selectedPlan && (
            <button
              onClick={handleChangePlan}
              disabled={isProcessing}
              data-testid="change-plan-button"
            >
              {isProcessing ? 'Processing...' : 'Change Plan'}
            </button>
          )}
        </div>
      </div>
    );
  };
  
  // Tests for viewing subscription plans
  describe('Viewing Subscription Plans', () => {
    it('GIVEN a user is browsing plans WHEN the plans load THEN they see all available subscription options', async () => {
      render(<SubscriptionPlans />);
      
      // Verify loading state appears
      expect(screen.getByTestId('loading')).toBeInTheDocument();
      
      // Verify plans are displayed
      await waitFor(() => {
        expect(screen.getByTestId('plans-container')).toBeInTheDocument();
      });
      
      // Verify multiple plans are shown
      const plans = screen.getAllByTestId(/^plan-/);
      expect(plans.length).toBeGreaterThan(1);
      
      // Verify plan details are displayed
      const premiumPlan = screen.getByTestId('plan-plan-premium');
      expect(premiumPlan).toHaveTextContent('Premium');
      expect(premiumPlan).toHaveTextContent('19.99');
      expect(premiumPlan).toHaveTextContent('Most Popular');
    });
    
    it('GIVEN a user is viewing plans WHEN they select a plan THEN they can proceed to checkout', async () => {
      const user = userEvent.setup();
      render(<SubscriptionPlans />);
      
      // Wait for plans to load
      await waitFor(() => {
        expect(screen.getByTestId('plans-container')).toBeInTheDocument();
      });
      
      // Select a plan
      await user.click(screen.getByTestId('select-plan-plan-basic'));
      
      // Verify subscribe button appears
      expect(screen.getByTestId('subscribe-button')).toBeInTheDocument();
      
      // Click subscribe
      await user.click(screen.getByTestId('subscribe-button'));
      
      // Verify checkout redirect appears
      await waitFor(() => {
        expect(screen.getByTestId('checkout-redirect')).toBeInTheDocument();
        expect(screen.getByTestId('checkout-link')).toHaveAttribute('href');
      });
    });
    
    it('GIVEN an error occurs WHEN loading plans THEN the user sees an error message', async () => {
      // Override handler to simulate error
      server.use(
        http.get('/api/subscription/plans', () => {
          return new HttpResponse(null, { status: 500 });
        })
      );
      
      render(<SubscriptionPlans />);
      
      // Verify error message appears
      await waitFor(() => {
        expect(screen.getByTestId('error')).toBeInTheDocument();
      });
    });
  });
  
  // Tests for managing existing subscription
  describe('Managing Current Subscription', () => {
    it('GIVEN a user has an active subscription WHEN they view subscription details THEN they see their current plan', async () => {
      render(<SubscriptionManager />);
      
      // Verify loading state appears
      expect(screen.getByTestId('loading')).toBeInTheDocument();
      
      // Verify subscription details are displayed
      await waitFor(() => {
        expect(screen.getByTestId('subscription-manager')).toBeInTheDocument();
        expect(screen.getByTestId('current-plan')).toBeInTheDocument();
      });
      
      // Verify subscription status is displayed
      expect(screen.getByTestId('subscription-status')).toHaveTextContent('active');
      
      // Verify auto-renew status is displayed
      expect(screen.getByTestId('auto-renew-status')).toBeInTheDocument();
    });
    
    it('GIVEN a user wants to disable auto-renewal WHEN they toggle auto-renew THEN their subscription is updated', async () => {
      const user = userEvent.setup();
      render(<SubscriptionManager />);
      
      // Wait for subscription details to load
      await waitFor(() => {
        expect(screen.getByTestId('subscription-manager')).toBeInTheDocument();
      });
      
      // Check initial auto-renew status (assuming it's enabled by default)
      expect(screen.getByTestId('auto-renew-status')).toHaveTextContent('Yes');
      
      // Click toggle auto-renew button
      await user.click(screen.getByTestId('toggle-auto-renew'));
      
      // Verify auto-renew status is updated
      await waitFor(() => {
        expect(screen.getByTestId('auto-renew-status')).toHaveTextContent('No');
      });
      
      // Verify success message appears
      expect(screen.getByTestId('success-message')).toBeInTheDocument();
    });
    
    it('GIVEN a user wants to cancel WHEN they cancel their subscription THEN it is marked as canceled', async () => {
      // Mock window.confirm to return true
      window.confirm = jest.fn().mockReturnValue(true);
      
      const user = userEvent.setup();
      render(<SubscriptionManager />);
      
      // Wait for subscription details to load
      await waitFor(() => {
        expect(screen.getByTestId('subscription-manager')).toBeInTheDocument();
      });
      
      // Click cancel subscription button
      await user.click(screen.getByTestId('cancel-subscription'));
      
      // Verify confirmation dialog was shown
      expect(window.confirm).toHaveBeenCalled();
      
      // Verify subscription status is updated
      await waitFor(() => {
        expect(screen.getByTestId('subscription-status')).toHaveTextContent('cancelled');
      });
      
      // Verify success message appears
      expect(screen.getByTestId('success-message')).toHaveTextContent('Your subscription has been canceled');
    });
  });
  
  // Tests for changing subscription plan
  describe('Changing Subscription Plan', () => {
    it('GIVEN a user wants to upgrade WHEN they select a higher-tier plan THEN their subscription is upgraded', async () => {
      const user = userEvent.setup();
      render(<SubscriptionManager />);
      
      // Wait for subscription details to load
      await waitFor(() => {
        expect(screen.getByTestId('subscription-manager')).toBeInTheDocument();
      });
      
      // Select premium plan (assuming user is on basic)
      await user.click(screen.getByTestId('plan-option-plan-premium'));
      
      // Click change plan button
      await user.click(screen.getByTestId('change-plan-button'));
      
      // Verify success message appears
      await waitFor(() => {
        expect(screen.getByTestId('success-message')).toBeInTheDocument();
      });
      
      // Verify current plan is updated
      expect(screen.getByTestId('current-plan')).toHaveTextContent('Premium');
    });
    
    it('GIVEN a user wants to downgrade WHEN they select a lower-tier plan THEN their subscription is downgraded', async () => {
      // Override handler to return premium subscription
      server.use(
        http.get('/api/subscription/current', () => {
          return HttpResponse.json(createMockSubscription({
            planId: 'plan-premium'
          }));
        })
      );
      
      const user = userEvent.setup();
      render(<SubscriptionManager />);
      
      // Wait for subscription details to load
      await waitFor(() => {
        expect(screen.getByTestId('current-plan')).toHaveTextContent('Premium');
      });
      
      // Select basic plan
      await user.click(screen.getByTestId('plan-option-plan-basic'));
      
      // Click change plan button
      await user.click(screen.getByTestId('change-plan-button'));
      
      // Verify success message appears
      await waitFor(() => {
        expect(screen.getByTestId('success-message')).toBeInTheDocument();
      });
      
      // Verify message indicates when changes take effect
      expect(screen.getByTestId('success-message')).toHaveTextContent('end of the current billing cycle');
    });
  });
  
  // Tests for users without subscriptions
  describe('No Active Subscription', () => {
    it('GIVEN a user has no subscription WHEN they view the subscription page THEN they see a prompt to subscribe', async () => {
      // Override handler to return null for current subscription
      server.use(
        http.get('/api/subscription/current', () => {
          return new HttpResponse(null, { status: 404 });
        })
      );
      
      render(<SubscriptionManager />);
      
      // Verify no-subscription message appears
      await waitFor(() => {
        expect(screen.getByTestId('no-subscription')).toBeInTheDocument();
      });
      
      // Verify link to subscription plans is shown
      expect(screen.getByText('View Subscription Plans')).toBeInTheDocument();
    });
  });
}); 