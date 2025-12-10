/**
 * Style utility functions for consistent styling
 */
import { colors } from './colors';

export const styleUtils = {
  input: {
    base: {
      borderColor: colors.borderGray,
      borderWidth: '1px',
      borderStyle: 'solid',
    },
  },
  button: {
    primary: {
      backgroundColor: colors.primaryBlue,
      color: colors.white,
    },
    primaryHover: {
      backgroundColor: colors.darkBlue,
    },
  },
  card: {
    backgroundColor: colors.white,
    borderColor: colors.borderGray,
  },
  text: {
    primary: { color: colors.primaryText },
    secondary: { color: colors.secondaryText },
  },
  background: {
    light: { backgroundColor: colors.lightBg },
  },
  border: {
    gray: { borderColor: colors.borderGray },
  },
};

