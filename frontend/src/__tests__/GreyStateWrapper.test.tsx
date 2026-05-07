import { render, screen } from '@testing-library/react';
import GreyStateWrapper from '../components/shared/GreyStateWrapper';

describe('GreyStateWrapper', () => {
  test('renders children at full opacity when not grey', () => {
    render(
      <GreyStateWrapper operationalState="On">
        <div data-testid="child">child</div>
      </GreyStateWrapper>,
    );
    const wrapper = screen.getByTestId('grey-state-wrapper');
    expect(wrapper.style.opacity).toBe('1');
    expect(wrapper.style.filter).toBe('none');
    expect(screen.queryByTestId('grey-state-badge')).toBeNull();
  });

  test('applies grey treatment and overlays StateBadge when off', () => {
    render(
      <GreyStateWrapper operationalState="Off" lastMeasured={null}>
        <div>child</div>
      </GreyStateWrapper>,
    );
    const wrapper = screen.getByTestId('grey-state-wrapper');
    expect(wrapper.style.opacity).toBe('0.4');
    expect(wrapper.style.filter).toContain('grayscale');
    expect(screen.getByTestId('grey-state-badge')).toBeInTheDocument();
  });

  test('badgePlacement="none" suppresses overlay even when grey', () => {
    render(
      <GreyStateWrapper operationalState="Off" badgePlacement="none">
        <div>child</div>
      </GreyStateWrapper>,
    );
    expect(screen.queryByTestId('grey-state-badge')).toBeNull();
  });
});