ALTER TABLE public.customers ADD COLUMN account_tier text;
UPDATE public.customers SET account_tier = 'standard';
ALTER TABLE public.customers ALTER COLUMN account_tier SET NOT NULL;
UPDATE public.customers SET email = 'changed@example.invalid' WHERE id = 1;
