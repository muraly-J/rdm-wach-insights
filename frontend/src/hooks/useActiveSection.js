import { useState, useEffect, useRef } from 'react';

// ─────────────────────────────────────────────────────────────────────────────
// useActiveSection Hook
// Tracks which plot/metric the user is currently viewing via IntersectionObserver
//
// Usage:
//   const { activeSection, elementRefs } = useActiveSection(['energy', 'pf', 'thd']);
//   return (
//     <div ref={elementRefs.energy}>...</div>
//     <div ref={elementRefs.pf}>...</div>
//   );
// ─────────────────────────────────────────────────────────────────────────────

export function useActiveSection(metricKeys = []) {
  const [activeSection, setActiveSection] = useState(null);
  const elementRefs = useRef({});
  const observerRef = useRef(null);

  // Create refs for each metric
  useEffect(() => {
    const refs = {};
    metricKeys.forEach((key) => {
      refs[key] = { current: null };
    });
    elementRefs.current = refs;

    return () => {
      // Cleanup observer
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [metricKeys]);

  // Set up IntersectionObserver
  useEffect(() => {
    const observerOptions = {
      root: null,
      rootMargin: '-40% 0px -55% 0px',
      threshold: 0,
    };

    observerRef.current = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          // Get metric key from data attribute or element id
          const metricKey = entry.target.getAttribute('data-metric');
          if (metricKey) {
            setActiveSection(metricKey);
          }
        }
      });
    }, observerOptions);

    // Observe all metric elements
    Object.values(elementRefs.current).forEach((ref) => {
      if (ref && ref.current) {
        observerRef.current.observe(ref.current);
      }
    });

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [elementRefs]);

  // Helper to manually set active section (for click interactions)
  const setActiveSectionManually = (metricKey) => {
    setActiveSection(metricKey);
  };

  return {
    activeSection,
    elementRefs,
    setActiveSectionManually,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// useChatContext Hook
// Provides context-aware AI messages based on active section
//
// Usage:
//   const chatMessage = useChatContext(activeSection);
//   // Returns message like: "I see you're looking at Energy Anomaly..."
// ─────────────────────────────────────────────────────────────────────────────

export function useChatContext(activeSection) {
  const chatPrompts = {
    energy_anomaly: (currentValue) =>
      `I see you're looking at Energy Anomaly metrics.${
        currentValue ? ` The current value is ${currentValue}.` : ''
      } Would you like me to analyze the energy patterns over time?`,

    pf_degradation: (currentValue) =>
      `I see you're examining Power Factor degradation.${
        currentValue ? ` Current PF: ${currentValue}.` : ''
      } Would you like to see which devices have the worst power factor?`,

    phase_imbalance: (currentValue) =>
      `I see you're looking at Phase Imbalance data.${
        currentValue ? ` Current imbalance: ${currentValue}.` : ''
      } Would you like me to analyze the three-phase balance?`,

    thd_drift: (currentValue) =>
      `I see you're reviewing THD Drift metrics.${
        currentValue ? ` Current THD: ${currentValue}.` : ''
      } Would you like to see harmonic analysis recommendations?`,

    overload: (currentValue) =>
      `I see you're analyzing Overload metrics.${
        currentValue ? ` Current load: ${currentValue}.` : ''
      } Would you like me to find the peak overload events?`,
  };

  // Default message when no section is active
  const defaultPrompt = () =>
    "I see you're exploring the AHU fleet metrics. Which metric would you like to analyze? I can help you find inefficiencies, compare devices, or predict future power consumption.";

  const getChatPrompt = () => {
    if (!activeSection) return defaultPrompt();

    // Get the current value (would come from store or API)
    const currentValue = null; // TODO: Fetch from state

    return chatPrompts[activeSection]?.(currentValue) || defaultPrompt();
  };

  const getActionableInsights = () => {
    if (!activeSection) return [];

    switch (activeSection) {
      case 'energy_anomaly':
        return [
          'Identify high-energy periods',
          'Compare against similar AHUs',
          'Predict future consumption',
        ];
      case 'pf_degradation':
        return [
          'Capacitor bank recommendations',
          'Load factor analysis',
          'Power quality audit',
        ];
      case 'phase_imbalance':
        return [
          'Three-phase load balancing',
          'Harmonic filtering recommendations',
          'Equipment stress assessment',
        ];
      case 'thd_drift':
        return [
          'Harmonic resonance analysis',
          'Transformer loading check',
          'VFD compatibility review',
        ];
      case 'overload':
        return [
          'Peak demand management',
          'Load shedding recommendations',
          'Capacity planning',
        ];
      default:
        return ['General analysis', 'Data export', 'System health report'];
    }
  };

  return {
    chatPrompt: getChatPrompt(),
    actionableInsights: getActionableInsights(),
  };
}
