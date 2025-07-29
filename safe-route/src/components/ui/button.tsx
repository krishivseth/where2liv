import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/30 focus-visible:ring-2 border",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground border-primary/20 hover:bg-primary/90 minimal-shadow",
        destructive:
          "bg-destructive text-destructive-foreground border-destructive/20 hover:bg-destructive/90 minimal-shadow",
        outline:
          "border-border bg-background hover:bg-accent hover:text-accent-foreground minimal-shadow",
        secondary:
          "bg-secondary text-secondary-foreground border-secondary/20 hover:bg-secondary/80 minimal-shadow",
        ghost:
          "border-transparent hover:bg-accent hover:text-accent-foreground",
        link: "border-transparent text-primary underline-offset-4 hover:underline",
        pastel: 
          "bg-accent text-accent-foreground border-accent/20 hover:bg-accent/80 minimal-shadow",
        "pastel-green":
          "bg-green-50 text-green-700 border-green-200 hover:bg-green-100 minimal-shadow",
        "pastel-blue":
          "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100 minimal-shadow",
        "pastel-purple":
          "bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100 minimal-shadow",
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        sm: "h-8 px-3 has-[>svg]:px-2.5",
        lg: "h-10 px-6 has-[>svg]:px-4",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
