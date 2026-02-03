'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  /* Base styles */
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary:
          'bg-crimson-600 text-white shadow-md hover:bg-crimson-700 hover:shadow-lg hover:scale-102 active:scale-98',
        secondary:
          'bg-white text-stone-900 border-2 border-stone-300 shadow-sm hover:bg-stone-50 hover:border-crimson-600 hover:shadow-md',
        success:
          'bg-forest-600 text-white shadow-md hover:bg-forest-700 hover:shadow-lg hover:scale-102 active:scale-98',
        outline:
          'border-2 border-primary bg-transparent text-primary hover:bg-crimson-50',
        ghost:
          'bg-transparent text-crimson-600 hover:bg-crimson-50 hover:text-crimson-700',
        link:
          'text-crimson-600 underline-offset-4 hover:underline',
      },
      size: {
        sm: 'h-9 px-4 text-sm',
        md: 'h-11 px-6 text-base',
        lg: 'h-13 px-8 text-lg',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
  VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);

Button.displayName = 'Button';

export { Button, buttonVariants };
