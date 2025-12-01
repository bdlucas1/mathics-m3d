(* TODO: axes should be centered; maybe use plotly native polar plot for this? *)
(* Interactive speed is marginal for this plot *)
Manipulate[
    PolarPlot[
        Sqrt[t*a],
        {t, 0, 16 Pi},
        PlotRange -> {{-8,8}, {-8,8}}
    ],
    {{a,1}, 0.7, 1.3, 0.01}
]
