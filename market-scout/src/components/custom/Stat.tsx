type TStatProps = {
    label: string;
    value: string;
    hint?: string;
};

const Stat = ({ label, value, hint }: TStatProps) => (
    <div>
        <dt className="text-xs text-muted-foreground">{label}</dt>
        <dd className="text-lg font-semibold tabular-nums">{value}</dd>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
);

export default Stat;
