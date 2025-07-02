import { Box, Typography } from '@mui/material';

interface LogoProps {
  size?: 'small' | 'medium' | 'large';
  showText?: boolean;
  textVariant?: 'h4' | 'h5' | 'h6' | 'body1' | 'body2';
  sx?: any;
}

const sizes = {
  small: 24,
  medium: 32,
  large: 48,
};

export default function Logo({ 
  size = 'medium', 
  showText = true, 
  textVariant = 'h6',
  sx = {}
}: LogoProps) {
  const logoSize = sizes[size];

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        ...sx
      }}
    >
      <Box
        component="img"
        src="/logo.png"
        alt="Smart ToDo Admin Logo"
        sx={{
          width: logoSize,
          height: logoSize,
          objectFit: 'contain',
        }}
      />
      {showText && (
        <Typography
          variant={textVariant}
          component="div"
          sx={{
            fontWeight: 600,
            color: 'inherit',
            whiteSpace: 'nowrap',
          }}
        >
          Smart-ToDo Admin
        </Typography>
      )}
    </Box>
  );
}