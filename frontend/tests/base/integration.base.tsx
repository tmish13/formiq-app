import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent, { UserEvent } from '@testing-library/user-event';
import { renderWithProviders } from './component.base';

export class IntegrationTest {
  protected user: UserEvent;

  constructor() {
    this.user = userEvent.setup();
  }

  protected render(ui: React.ReactElement, options = {}) {
    const result = renderWithProviders(ui, options);
    return {
      ...result,
      user: this.user,
    };
  }

  protected async waitForLoadingToFinish() {
    return waitFor(
      () => {
        const loader = screen.queryByRole('progressbar');
        if (loader) {
          throw new Error('Still loading');
        }
      },
      { timeout: 4000 }
    );
  }

  protected async fillForm(fields: Record<string, string>) {
    for (const [label, value] of Object.entries(fields)) {
      const input = screen.getByLabelText(label);
      await this.user.clear(input);
      await this.user.type(input, value);
    }
  }

  protected async submitForm(submitButtonText = 'Submit') {
    const submitButton = screen.getByRole('button', { name: submitButtonText });
    await this.user.click(submitButton);
  }

  protected async selectOption(label: string, optionText: string) {
    const select = screen.getByLabelText(label);
    await this.user.click(select);
    const option = screen.getByRole('option', { name: optionText });
    await this.user.click(option);
  }

  protected async uploadFile(inputLabel: string, file: File) {
    const input = screen.getByLabelText(inputLabel);
    await this.user.upload(input, file);
  }
} 