import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const BOOK_HREF = "#book";

export const SIGNUP_HREF = "/signup";
export const LOGIN_HREF = "/login";
