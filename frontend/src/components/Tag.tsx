import { type JSX } from "react";

export const Tag = (props: { efficiency: number }): JSX.Element => {
  return (
    <div
      className={`${
        props.efficiency < 75
          ? "bg-red-200 text-red-800"
          : "bg-green-200 text-green-800"
      } rounded px-2 py-0.5 text-base w-fit font-semibold`}
    >
      {props.efficiency < 75 ? "Inefficient" : "Efficient"}
    </div>
  );
};
