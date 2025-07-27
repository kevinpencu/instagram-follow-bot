import { useState } from "react";
import { Button } from "~/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Loader2 } from "lucide-react";

interface WorkerInputModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (maxWorkers: number) => Promise<void>;
  actionType: "start-all" | "start-selected";
  selectedCount?: number;
  isLoading: boolean;
}

export function WorkerInputModal({
  isOpen,
  onClose,
  onConfirm,
  actionType,
  selectedCount,
  isLoading,
}: WorkerInputModalProps) {
  const [maxWorkers, setMaxWorkers] = useState<string>("4");
  const [error, setError] = useState<string>("");

  const handleConfirm = async () => {
    const workersNum = parseInt(maxWorkers, 10);
    
    if (isNaN(workersNum) || workersNum <= 0) {
      setError("Please enter a valid positive number");
      return;
    }
    
    setError("");
    await onConfirm(workersNum);
  };

  const handleClose = () => {
    setError("");
    setMaxWorkers("4");
    onClose();
  };

  const getTitle = () => {
    return actionType === "start-all" ? "Start All Profiles" : "Start Selected Profiles";
  };

  const getDescription = () => {
    const baseText = "Specify the number of concurrent workers to process profiles.";
    if (actionType === "start-selected" && selectedCount) {
      return `${baseText} You have ${selectedCount} profile${selectedCount === 1 ? '' : 's'} selected.`;
    }
    return baseText;
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{getTitle()}</DialogTitle>
          <DialogDescription>{getDescription()}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="maxWorkers" className="text-right">
              Workers
            </Label>
            <Input
              id="maxWorkers"
              type="number"
              min="1"
              max="20"
              value={maxWorkers}
              onChange={(e) => setMaxWorkers(e.target.value)}
              className="col-span-3"
              placeholder="4"
              disabled={isLoading}
            />
          </div>
          {error && (
            <div className="text-sm text-destructive text-center">
              {error}
            </div>
          )}
          <div className="text-xs text-muted-foreground text-center">
            Default: 4 workers. Higher values may increase load on your system.
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Start
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
