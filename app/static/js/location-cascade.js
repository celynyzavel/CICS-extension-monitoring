function initLocationCascade(config) {

    const provinceSelect = document.getElementById(config.provinceSelectId);
    const citySelect = document.getElementById(config.citySelectId);
    const barangaySelect = document.getElementById(config.barangaySelectId);

    const provinceInput = document.getElementById(config.provinceInputId);
    const cityInput = document.getElementById(config.cityInputId);
    const barangayInput = document.getElementById(config.barangayInputId);

    const initialProvince = config.initialProvince || "";
    const initialCity = config.initialCity || "";
    const initialBarangay = config.initialBarangay || "";

    function resetSelect(select, placeholder) {

        select.innerHTML = "";

        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = placeholder;

        select.appendChild(opt);

        select.disabled = false;
    }
    function fillSelect(select, items, matchName) {

        let matchedOption = null;

        items.forEach(function (item) {

            const opt = document.createElement("option");

            opt.value = item.code;
            opt.textContent = item.name;
            opt.dataset.name = item.name;

            select.appendChild(opt);

            if (
                matchName &&
                item.name.trim().toLowerCase() ===
                matchName.trim().toLowerCase()
            ) {
                matchedOption = opt;
            }

        });

        if (matchedOption) {
            matchedOption.selected = true;
        }

        return matchedOption;
    }

    function loadProvinces() {

        resetSelect(provinceSelect, "Loading provinces...");

        fetch("/api/locations/provinces")

            .then(function (res) {
                return res.json();
            })

            .then(function (provinces) {

                resetSelect(
                    provinceSelect,
                    "Select Province"
                );

                const matched = fillSelect(
                    provinceSelect,
                    provinces,
                    initialProvince
                );

                if (matched) {

                    provinceInput.value =
                        matched.dataset.name;

                    loadCities(
                        matched.value,
                        initialCity
                    );

                } else {

                    resetSelect(
                        citySelect,
                        "Select City/Municipality"
                    );

                    resetSelect(
                        barangaySelect,
                        "Select Barangay"
                    );
                }

            })

            .catch(function () {

                resetSelect(
                    provinceSelect,
                    "Unable to load provinces"
                );

            });
    }


    function loadCities(provinceCode, preselectCity = "") {

        resetSelect(
            citySelect,
            "Loading cities/municipalities..."
        );

        resetSelect(
            barangaySelect,
            "Select Barangay"
        );


        if (!provinceCode) {

            resetSelect(
                citySelect,
                "Select City/Municipality"
            );

            return;
        }


        fetch(
            "/api/locations/cities?province_code=" +
            encodeURIComponent(provinceCode)
        )

            .then(function (res) {
                return res.json();
            })

            .then(function (cities) {

                resetSelect(
                    citySelect,
                    "Select City/Municipality"
                );

                const matched = fillSelect(
                    citySelect,
                    cities,
                    preselectCity
                );


                if (matched) {

                    cityInput.value =
                        matched.dataset.name;

                    loadBarangays(
                        matched.value,
                        initialBarangay
                    );
                }

            })

            .catch(function () {

                resetSelect(
                    citySelect,
                    "Unable to load cities/municipalities"
                );

            });
    }


    function loadBarangays(cityCode, preselectBarangay = "") {

        resetSelect(
            barangaySelect,
            "Loading barangays..."
        );


        if (!cityCode) {

            resetSelect(
                barangaySelect,
                "Select Barangay"
            );

            return;
        }


        fetch(
            "/api/locations/barangays?city_code=" +
            encodeURIComponent(cityCode)
        )

            .then(function (res) {
                return res.json();
            })

            .then(function (barangays) {

                resetSelect(
                    barangaySelect,
                    "Select Barangay"
                );

                const matched = fillSelect(
                    barangaySelect,
                    barangays,
                    preselectBarangay
                );


                if (matched) {

                    barangayInput.value =
                        matched.dataset.name;
                }

            })

            .catch(function () {

                resetSelect(
                    barangaySelect,
                    "Unable to load barangays"
                );

            });
    }

    provinceSelect.addEventListener(
        "change",
        function () {

            const selected =
                provinceSelect.options[
                    provinceSelect.selectedIndex
                ];


            provinceInput.value =
                selected && selected.value
                    ? selected.dataset.name
                    : "";


            cityInput.value = "";
            barangayInput.value = "";


            loadCities(
                selected ? selected.value : ""
            );
        }
    );


    citySelect.addEventListener(
        "change",
        function () {

            const selected =
                citySelect.options[
                    citySelect.selectedIndex
                ];


            cityInput.value =
                selected && selected.value
                    ? selected.dataset.name
                    : "";


            barangayInput.value = "";


            loadBarangays(
                selected ? selected.value : ""
            );
        }
    );

    barangaySelect.addEventListener(
        "change",
        function () {

            const selected =
                barangaySelect.options[
                    barangaySelect.selectedIndex
                ];


            barangayInput.value =
                selected && selected.value
                    ? selected.dataset.name
                    : "";

        }
    );


    resetSelect(
        barangaySelect,
        "Select Barangay"
    );

    resetSelect(
        citySelect,
        "Select City/Municipality"
    );

    resetSelect(
        provinceSelect,
        "Select Province"
    );


    loadProvinces();
}