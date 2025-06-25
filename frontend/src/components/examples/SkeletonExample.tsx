import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import Skeleton from '../common/SkeletonLoader';
import { LoadingSpinner } from '../atoms/LoadingSpinner';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

const ExampleContainer = styled.div`
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.lg', '1.5rem')};
  max-width: 800px;
  margin: 0 auto;
`;

const Section = styled.div`
  margin-bottom: ${({ theme }) => getThemeValue(theme, 'spacing.xl', '2rem')};
`;

const SectionTitle = styled.h2`
  margin-bottom: ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', '#2D3748')};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.semibold', '600')};
`;

const ButtonGroup = styled.div`
  margin-bottom: ${({ theme }) => getThemeValue(theme, 'spacing.lg', '1.5rem')};
  display: flex;
  gap: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '0.75rem')};
`;

const Button = styled.button`
  padding: ${({ theme }) => `${getThemeValue(theme, 'spacing.sm', '0.75rem')} ${getThemeValue(theme, 'spacing.md', '1rem')}`};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.primary', '#4D7CFE')};
  color: white;
  border: none;
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', '0.5rem')};
  cursor: pointer;
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', '500')};
  transition: background-color ${({ theme }) => getThemeValue(theme, 'transitions.medium', '0.3s')};

  &:hover {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.primaryDark', '#2E5BFF')};
  }

  &:disabled {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.disabled', fallbacks.color.disabled)};
    cursor: not-allowed;
  }
`;

const FlexRow = styled.div`
  display: flex;
  gap: ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
  flex-wrap: wrap;
`;

const SkeletonExample: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [activeDemo, setActiveDemo] = useState<string | null>(null);

  // Simulate data loading
  useEffect(() => {
    if (activeDemo) {
      setLoading(true);
      const timer = setTimeout(() => {
        setLoading(false);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [activeDemo]);

  return (
    <ExampleContainer>
      <SectionTitle>Skeleton Loading Examples</SectionTitle>
      
      <ButtonGroup>
        <Button onClick={() => setActiveDemo('text')}>Text Example</Button>
        <Button onClick={() => setActiveDemo('profiles')}>Profile Cards</Button>
        <Button onClick={() => setActiveDemo('table')}>Table Example</Button>
        <Button onClick={() => setActiveDemo('mixed')}>Mixed Components</Button>
      </ButtonGroup>

      {activeDemo === 'text' && (
        <Section>
          <SectionTitle>Text Skeleton</SectionTitle>
          {loading ? (
            <>
              <Skeleton variant="text" width="80%" height="32px" />
              <Skeleton variant="text" count={4} />
              <Skeleton variant="text" width="60%" />
            </>
          ) : (
            <>
              <h1>Article Title Goes Here</h1>
              <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam euismod metus vel sem bibendum, at viverra nunc elementum. Sed euismod est vel diam bibendum, vitae aliquet mauris tempor.</p>
              <p>Vivamus elementum est ac quam malesuada, vel pellentesque nisl efficitur. Curabitur vestibulum turpis vel mauris pretium, id sagittis lorem rhoncus.</p>
              <p>Praesent sit amet erat et dolor mattis mollis vel non erat. Duis ut eros a velit auctor pellentesque.</p>
              <p>Nulla facilisi. Pellentesque habitant morbi tristique senectus.</p>
            </>
          )}
        </Section>
      )}

      {activeDemo === 'profiles' && (
        <Section>
          <SectionTitle>Profile Cards</SectionTitle>
          {loading ? (
            <FlexRow>
              <Skeleton variant="card" />
              <Skeleton variant="card" />
              <Skeleton variant="card" />
            </FlexRow>
          ) : (
            <FlexRow>
              <div>User Profile 1 Content</div>
              <div>User Profile 2 Content</div>
              <div>User Profile 3 Content</div>
            </FlexRow>
          )}
        </Section>
      )}

      {activeDemo === 'table' && (
        <Section>
          <SectionTitle>Table Data</SectionTitle>
          {loading ? (
            <Skeleton variant="table" count={5} />
          ) : (
            <div>Table with 5 rows of data</div>
          )}
        </Section>
      )}

      {activeDemo === 'mixed' && (
        <Section>
          <SectionTitle>Mixed Components</SectionTitle>
          {loading ? (
            <>
              <Skeleton variant="text" width="70%" height="32px" />
              <FlexRow>
                <div style={{ width: "30%" }}>
                  <Skeleton variant="circular" width="100px" height="100px" />
                </div>
                <div style={{ width: "70%" }}>
                  <Skeleton variant="text" count={3} />
                </div>
              </FlexRow>
              <Skeleton variant="list" count={3} />
            </>
          ) : (
            <>
              <h2>Dashboard Overview</h2>
              <FlexRow>
                <div>User Profile Image</div>
                <div>User Information</div>
              </FlexRow>
              <div>Activity List</div>
            </>
          )}
        </Section>
      )}

      {!activeDemo && (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <p>Select a demo to see skeleton loaders in action</p>
          <LoadingSpinner size="medium" />
        </div>
      )}
    </ExampleContainer>
  );
};

export default SkeletonExample; 