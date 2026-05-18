"use client"

import React from 'react'

export default function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className="border rounded p-2 w-full focus:ring-2" {...props} />
}
