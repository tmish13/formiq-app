import React, { useState, useRef } from 'react';
import styled from 'styled-components';
import { useAuth } from '../../contexts/AuthContext';
import { User } from '../../types/auth';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ErrorMessage } from '../common/ErrorMessage';

const ProfileContainer = styled.div`
  max-width: 600px;
  margin: 2rem auto;
  padding: 2rem;
  background: ${({ theme }) => theme.colors.background.secondary};
  border-radius: ${({ theme }) => theme.borderRadius.lg};
  box-shadow: ${({ theme }) => theme.shadows.medium};
`;

const AvatarContainer = styled.div`
  position: relative;
  width: 150px;
  height: 150px;
  margin: 0 auto 2rem;
`;

const Avatar = styled.img`
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid ${({ theme }) => theme.colors.primary.main};
`;

const AvatarUpload = styled.div`
  position: absolute;
  bottom: 0;
  right: 0;
  background: ${({ theme }) => theme.colors.primary.main};
  border-radius: 50%;
  padding: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    transform: scale(1.1);
  }
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const InputGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`;

const Label = styled.label`
  font-weight: 500;
  color: ${({ theme }) => theme.colors.text.primary};
`;

const Input = styled.input`
  padding: 0.75rem;
  border: 1px solid ${({ theme }) => theme.colors.border.main};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  background: ${({ theme }) => theme.colors.background.main};
  color: ${({ theme }) => theme.colors.text.primary};

  &:focus {
    outline: none;
    border-color: ${({ theme }) => theme.colors.primary.main};
  }
`;

const Button = styled.button`
  padding: 0.75rem 1.5rem;
  background: ${({ theme }) => theme.colors.primary.main};
  color: ${({ theme }) => theme.colors.text.inverse};
  border: none;
  border-radius: ${({ theme }) => theme.borderRadius.md};
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: ${({ theme }) => theme.colors.primary.dark};
  }

  &:disabled {
    background: ${({ theme }) => theme.colors.disabled};
    cursor: not-allowed;
  }
`;

export const UserProfile: React.FC = () => {
  const { user, updateUser } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<Partial<User>>({
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    username: user?.username || '',
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsLoading(true);
      setError(null);
      
      const formData = new FormData();
      formData.append('avatar', file);
      
      const response = await apiService.profile.updateAvatar(formData);
      await updateUser({ avatarUrl: response.data.avatarUrl });
    } catch (err: any) {
      setError(err.message || 'Failed to update avatar');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setIsLoading(true);
      setError(null);
      
      await updateUser(formData);
      setIsEditing(false);
    } catch (err: any) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setIsLoading(false);
    }
  };

  if (!user) return null;

  return (
    <ProfileContainer>
      {error && <ErrorMessage message={error} />}
      
      <AvatarContainer>
        <Avatar 
          src={user.avatarUrl || '/default-avatar.png'} 
          alt={`${user.username}'s avatar`}
        />
        {isEditing && (
          <>
            <AvatarUpload onClick={handleAvatarClick}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19 7v2.99s-1.99.01-2 0V7h-3s.01-1.99 0-2h3V2h2v3h3v2h-3zm-3 4V8h-3V5H5c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2v-8h-3zM5 19l3-4 2 3 3-4 4 5H5z"/>
              </svg>
            </AvatarUpload>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleAvatarChange}
              accept="image/*"
              style={{ display: 'none' }}
            />
          </>
        )}
      </AvatarContainer>

      <Form onSubmit={handleSubmit}>
        <InputGroup>
          <Label htmlFor="username">Username</Label>
          <Input
            id="username"
            name="username"
            value={formData.username}
            onChange={handleInputChange}
            disabled={!isEditing}
          />
        </InputGroup>

        <InputGroup>
          <Label htmlFor="firstName">First Name</Label>
          <Input
            id="firstName"
            name="firstName"
            value={formData.firstName}
            onChange={handleInputChange}
            disabled={!isEditing}
          />
        </InputGroup>

        <InputGroup>
          <Label htmlFor="lastName">Last Name</Label>
          <Input
            id="lastName"
            name="lastName"
            value={formData.lastName}
            onChange={handleInputChange}
            disabled={!isEditing}
          />
        </InputGroup>

        <InputGroup>
          <Label>Email</Label>
          <Input
            value={user.email}
            disabled
          />
        </InputGroup>

        {isEditing ? (
          <div style={{ display: 'flex', gap: '1rem' }}>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? <LoadingSpinner size="small" /> : 'Save Changes'}
            </Button>
            <Button 
              type="button" 
              onClick={() => setIsEditing(false)}
              style={{ background: 'transparent', color: 'inherit', border: '1px solid' }}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <Button type="button" onClick={() => setIsEditing(true)}>
            Edit Profile
          </Button>
        )}
      </Form>
    </ProfileContainer>
  );
}; 