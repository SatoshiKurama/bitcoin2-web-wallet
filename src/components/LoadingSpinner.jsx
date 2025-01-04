import { Loader2 } from "lucide-react";

export const LoadingSpinner = ({ text = "Loading..." }) => {
  return (
    <div className="flex flex-col items-center justify-center p-4 space-y-2">
      <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      <p className="text-sm text-gray-500">{text}</p>
    </div>
  );
};

export default LoadingSpinner;