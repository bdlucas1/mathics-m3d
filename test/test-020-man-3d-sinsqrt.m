Manipulate[
    Plot3D[
        Sin[(x^2+y^2)*freq] / Sqrt[x^2+y^2+1] * amp, {x,-3,3}, {y,-3,3},
        PlotRange -> {Automatic, Automatic, {-0.5,0.7}}
    ],
    {{freq,1.0}, 0.1, 2.0, 0.1}, (* freq slider spec *)
    {{amp,1.0}, 0.0, 2.0, 0.1}  (* amp slider spec *)
]
