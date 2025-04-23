import React, { useState } from 'react';
import styled from 'styled-components';

interface FAQItem {
  question: string;
  answer: React.ReactNode;
  category?: string;
}

interface FAQModalProps {
  isOpen: boolean;
  onClose: () => void;
  faqItems: FAQItem[];
}

const ModalOverlay = styled.div<{ isOpen: boolean }>`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: ${({ isOpen }) => (isOpen ? 'flex' : 'none')};
  justify-content: center;
  align-items: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  background-color: #ffffff;
  border-radius: 8px;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
  padding: ${({ theme }) => theme.spacing.lg}px;
  position: relative;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
`;

const ModalHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid ${({ theme }) => theme.colors.border};
  padding-bottom: ${({ theme }) => theme.spacing.md}px;
  margin-bottom: ${({ theme }) => theme.spacing.md}px;
`;

const Title = styled.h2`
  margin: 0;
  color: ${({ theme }) => theme.colors.text};
  font-weight: 600;
`;

const CloseButton = styled.button`
  background: transparent;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: ${({ theme }) => theme.colors.text};
  
  &:hover {
    color: ${({ theme }) => theme.colors.primary.main};
  }
`;

const CategoryTabs = styled.div`
  display: flex;
  border-bottom: 1px solid ${({ theme }) => theme.colors.border};
  margin-bottom: ${({ theme }) => theme.spacing.md}px;
  overflow-x: auto;
  scrollbar-width: thin;
  
  &::-webkit-scrollbar {
    height: 4px;
  }
  
  &::-webkit-scrollbar-thumb {
    background-color: ${({ theme }) => theme.colors.border};
    border-radius: 4px;
  }
`;

const Tab = styled.button<{ isActive: boolean }>`
  padding: ${({ theme }) => theme.spacing.sm}px ${({ theme }) => theme.spacing.md}px;
  background: ${({ isActive, theme }) => isActive ? theme.colors.primary.main : 'transparent'};
  color: ${({ isActive, theme }) => isActive ? '#ffffff' : theme.colors.text};
  border: none;
  border-bottom: 2px solid ${({ isActive, theme }) => isActive ? theme.colors.primary.main : 'transparent'};
  cursor: pointer;
  font-weight: ${({ isActive }) => isActive ? '600' : '400'};
  white-space: nowrap;
  
  &:hover {
    background: ${({ isActive, theme }) => isActive ? theme.colors.primary.main : theme.colors.background};
  }
`;

const FAQList = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.spacing.md}px;
`;

const FAQItem = styled.div`
  border: 1px solid ${({ theme }) => theme.colors.border};
  border-radius: 4px;
  overflow: hidden;
`;

const Question = styled.button<{ isExpanded: boolean }>`
  width: 100%;
  text-align: left;
  padding: ${({ theme }) => theme.spacing.md}px;
  background-color: ${({ isExpanded, theme }) => isExpanded ? theme.colors.background : '#ffffff'};
  border: none;
  cursor: pointer;
  font-weight: 500;
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  &:hover {
    background-color: ${({ theme }) => theme.colors.background};
  }
  
  &::after {
    content: "${({ isExpanded }) => isExpanded ? '−' : '+'}";
    font-size: 20px;
    margin-left: ${({ theme }) => theme.spacing.sm}px;
  }
`;

const Answer = styled.div<{ isExpanded: boolean }>`
  padding: ${({ isExpanded, theme }) => isExpanded ? theme.spacing.md : 0}px;
  max-height: ${({ isExpanded }) => isExpanded ? '500px' : '0'};
  opacity: ${({ isExpanded }) => isExpanded ? 1 : 0};
  transition: all 0.3s ease-in-out;
  overflow: hidden;
  border-top: ${({ isExpanded, theme }) => isExpanded ? `1px solid ${theme.colors.border}` : 'none'};
`;

const SearchInput = styled.input`
  width: 100%;
  padding: ${({ theme }) => theme.spacing.sm}px;
  border: 1px solid ${({ theme }) => theme.colors.border};
  border-radius: 4px;
  margin-bottom: ${({ theme }) => theme.spacing.md}px;
  
  &:focus {
    outline: none;
    border-color: ${({ theme }) => theme.colors.primary.main};
  }
`;

export const FAQModal: React.FC<FAQModalProps> = ({ isOpen, onClose, faqItems }) => {
  const [expandedItem, setExpandedItem] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Extract unique categories
  const categories = ['All', ...Array.from(new Set(faqItems.map(item => item.category || 'General')))];
  const [activeCategory, setActiveCategory] = useState('All');
  
  const handleItemClick = (index: number) => {
    setExpandedItem(expandedItem === index ? null : index);
  };
  
  const handleTabClick = (category: string) => {
    setActiveCategory(category);
    setExpandedItem(null);
  };
  
  const filteredItems = faqItems.filter(item => {
    const matchesCategory = activeCategory === 'All' || item.category === activeCategory || (!item.category && activeCategory === 'General');
    const matchesSearch = searchQuery === '' || 
      item.question.toLowerCase().includes(searchQuery.toLowerCase()) || 
      (typeof item.answer === 'string' && item.answer.toLowerCase().includes(searchQuery.toLowerCase()));
    
    return matchesCategory && matchesSearch;
  });
  
  return (
    <ModalOverlay isOpen={isOpen} onClick={onClose}>
      <ModalContent onClick={e => e.stopPropagation()}>
        <ModalHeader>
          <Title>Frequently Asked Questions</Title>
          <CloseButton onClick={onClose}>&times;</CloseButton>
        </ModalHeader>
        
        <SearchInput 
          type="text" 
          placeholder="Search questions..." 
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
        
        <CategoryTabs>
          {categories.map(category => (
            <Tab 
              key={category} 
              isActive={activeCategory === category}
              onClick={() => handleTabClick(category)}
            >
              {category}
            </Tab>
          ))}
        </CategoryTabs>
        
        <FAQList>
          {filteredItems.length > 0 ? (
            filteredItems.map((item, index) => (
              <FAQItem key={index}>
                <Question 
                  isExpanded={expandedItem === index}
                  onClick={() => handleItemClick(index)}
                >
                  {item.question}
                </Question>
                <Answer isExpanded={expandedItem === index}>
                  {item.answer}
                </Answer>
              </FAQItem>
            ))
          ) : (
            <div>No matching questions found.</div>
          )}
        </FAQList>
      </ModalContent>
    </ModalOverlay>
  );
};

export default FAQModal; 