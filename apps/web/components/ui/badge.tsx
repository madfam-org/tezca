import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
    "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
    {
        variants: {
            variant: {
                default:
                    "border-transparent bg-stone-900 text-stone-50 hover:bg-stone-900/80",
                success:
                    "border-forest-200 bg-forest-100 text-forest-800 dark:bg-forest-900 dark:text-forest-200",
                warning:
                    "border-gold-200 bg-gold-100 text-gold-800 dark:bg-gold-900 dark:text-gold-200",
                error:
                    "border-crimson-200 bg-crimson-100 text-crimson-800 dark:bg-crimson-900 dark:text-crimson-200",
                secondary:
                    "border-stone-200 bg-stone-100 text-stone-900 hover:bg-stone-200/80",
                outline:
                    "text-stone-900 border-stone-300",
            },
        },
        defaultVariants: {
            variant: "default",
        },
    }
)

export interface BadgeProps
    extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
    return (
        <div className={cn(badgeVariants({ variant }), className)} {...props} />
    )
}

export { Badge, badgeVariants }
